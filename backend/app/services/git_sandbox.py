from __future__ import annotations

import dataclasses
import logging
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Only these remote hosts may be cloned to keep the sandbox from hitting
# internal networks (SSRF hardening).
ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "gitea.com"}

PYTHON_FILE_RE = re.compile(r"^[a-zA-Z0-9_]+\.py$")

# Paths never touched during a directory refactor.
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".tox",
    ".nox",
    "htmlcov",
    ".mypy_cache",
    ".ruff_cache",
}


class GitOperationError(RuntimeError):
    """Raised when a git subprocess fails or a repo is rejected."""


@dataclasses.dataclass
class TestRunResult:
    """Outcome of running the test suite inside a sandbox clone."""

    returncode: int
    success: bool
    stdout: str
    stderr: str
    duration_seconds: float

    def summary(self) -> str:
        if self.success:
            return f"Tests passed in {self.duration_seconds:.1f}s"
        tail = (self.stdout or self.stderr).strip().splitlines()
        return "Tests failed: " + " | ".join(tail[-5:])[:2000]


@dataclasses.dataclass
class FileChange:
    """A single refactored file within the sandbox clone."""

    rel_path: str
    before: str
    after: str
    applied_rules: list[str] = dataclasses.field(default_factory=list)


class GitSandboxService:
    """Clone, test, refactor, and clean up remote repositories in isolation.

    All subprocess calls use argument lists (never a shell) and every command
    is time-boxed so a malicious or broken repo cannot hang the pipeline.
    """

    # --- Repo validation --------------------------------------------------

    @staticmethod
    def validate_repo_url(repo_url: str) -> str:
        """Reject anything that is not a public HTTPS/SSH git URL."""
        url = repo_url.strip()
        if not url:
            raise GitOperationError("repo_url is required.")
        lowered = url.lower()
        # Only https or SSH URLs; forbid file://, git://, local paths, etc.
        if not (
            lowered.startswith("https://")
            or lowered.startswith("ssh://")
            or lowered.startswith("git@")
        ):
            raise GitOperationError(
                "Only HTTPS or SSH git URLs are allowed (no file:// or local paths)."
            )
        host = ""
        if lowered.startswith("git@"):
            host = lowered.split("@", 1)[1].split(":", 1)[0]
        elif lowered.startswith(("https://", "ssh://")):
            host = lowered.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
        if host not in ALLOWED_GIT_HOSTS:
            raise GitOperationError(f"git host '{host}' is not on the allowlist.")
        return url

    # --- Lifecycle --------------------------------------------------------

    @classmethod
    def clone_repository(
        cls,
        repo_url: str,
        branch: str = "main",
        depth: int = 1,
        extra_args: list[str] | None = None,
    ) -> str:
        """Clone a remote repo into a fresh temp dir and return its path.

        Runs synchronously (blocking). Callers in async contexts should wrap
        with `asyncio.to_thread` to avoid stalling the event loop.
        """
        url = cls.validate_repo_url(repo_url)
        workspace = Path(settings.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        project_dir = Path(tempfile.mkdtemp(prefix="omnimigrate_", dir=workspace))

        cmd = ["git", "clone", "--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        if extra_args:
            cmd += extra_args
        cmd += [url, str(project_dir)]

        try:
            cls._run(cmd, cwd=workspace, timeout=settings.git_clone_timeout_seconds)
        except GitOperationError as exc:
            shutil.rmtree(project_dir, ignore_errors=True)
            raise GitOperationError(f"Failed to clone {url}: {exc}") from exc

        size = cls._dir_size(project_dir)
        if size > settings.git_max_repo_bytes:
            shutil.rmtree(project_dir, ignore_errors=True)
            raise GitOperationError(
                f"Repository exceeds the {settings.git_max_repo_bytes // (1024 * 1024)} MB limit."
            )
        logger.info("Cloned %s (%s) in %.2f MB", url, branch, size / (1024 * 1024))
        return str(project_dir)

    @classmethod
    def run_tests(cls, project_dir: str) -> TestRunResult:
        """Run the repo's pytest suite and capture the outcome."""
        started = time.monotonic()
        cmd = ["python", "-m", "pytest", "-x", "-q", "--tb=short"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=settings.git_test_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(
                f"Test suite timed out after {settings.git_test_timeout_seconds}s."
            ) from exc
        except FileNotFoundError:
            raise GitOperationError("pytest is not available in the sandbox image.") from None

        success = proc.returncode == 0
        return TestRunResult(
            returncode=proc.returncode,
            success=success,
            stdout=(proc.stdout or ""),
            stderr=(proc.stderr or ""),
            duration_seconds=time.monotonic() - started,
        )

    @staticmethod
    def cleanup(project_dir: str) -> None:
        """Best-effort removal of a sandbox clone."""
        try:
            shutil.rmtree(project_dir, ignore_errors=True)
        except Exception:
            logger.warning("Failed to remove sandbox %s", project_dir)

    # --- Directory refactoring --------------------------------------------

    @classmethod
    def process_directory(
        cls, project_dir: str, refactor_fn, context_rule: str
    ) -> list[FileChange]:
        """Apply `refactor_fn(code, context_rule) -> code` to every Python file.

        Returns the list of files whose content actually changed so callers can
        report diffs and commit them.
        """
        changes: list[FileChange] = []
        root = Path(project_dir)
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            if cls._is_excluded(rel):
                continue
            try:
                before = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                after = refactor_fn(before, context_rule)
            except Exception:
                logger.warning("Refactor failed for %s", rel, exc_info=True)
                continue
            if after and after != before:
                path.write_text(after, encoding="utf-8")
                changes.append(FileChange(rel_path=rel, before=before, after=after))
        return changes

    @classmethod
    def heal_code_with_error(
        cls, project_dir: str, error_output: str, heal_fn, context_rule: str
    ) -> list[FileChange]:
        """Retry refactoring only the files implicated in a failed test run."""
        affected = cls._files_from_error(project_dir, error_output)
        changes: list[FileChange] = []
        root = Path(project_dir)
        for rel in affected:
            path = root / rel
            try:
                broken = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                healed = heal_fn(broken, error_output, context_rule)
            except Exception:
                logger.warning("Healing failed for %s", rel, exc_info=True)
                continue
            if healed and healed != broken:
                path.write_text(healed, encoding="utf-8")
                changes.append(FileChange(rel_path=rel, before=broken, after=healed))
        return changes

    # --- Helpers ----------------------------------------------------------

    @staticmethod
    def _is_excluded(rel_path: str) -> bool:
        parts = rel_path.split("/")
        return any(part in EXCLUDED_DIRS for part in parts)

    @staticmethod
    def _files_from_error(project_dir: str, error_output: str) -> list[str]:
        root = Path(project_dir).resolve()
        files: list[str] = []
        for match in re.finditer(r'File "([^"]+\.py)"', error_output or ""):
            candidate = match.group(1)
            if Path(candidate).is_absolute():
                try:
                    resolved = Path(candidate).resolve()
                    if root in resolved.parents or resolved == root:
                        files.append(resolved.relative_to(root).as_posix())
                except (OSError, ValueError):
                    continue
            else:
                # Relative to project root, e.g. "src/mod.py" or "tests/test_x.py".
                clean = candidate.replace("\\", "/").lstrip("./")
                if (root / clean).exists():
                    files.append(clean)
        return sorted(set(files))

    @staticmethod
    def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc
        if proc.returncode != 0:
            raise GitOperationError(f"Command failed: {' '.join(cmd)}\n{proc.stderr}")
        return proc

    @staticmethod
    def _dir_size(path: Path) -> int:
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
        return total
