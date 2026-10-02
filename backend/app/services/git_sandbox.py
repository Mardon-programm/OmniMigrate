from __future__ import annotations

import dataclasses
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import structlog

from app.core.config import settings
from app.services.sandbox import SandboxConfig, DynamicSandbox

logger = structlog.get_logger(__name__)

# Global dynamic sandbox for test runs
_git_sandbox = DynamicSandbox(
    config=SandboxConfig(
        timeout_seconds=settings.git_test_timeout_seconds,
        memory_limit="1g",
        cpu_limit=2.0,
        network_disabled=False,  # Tests may need network
        read_only_rootfs=False,
    ),
    enabled=settings.sandbox_enabled,
    image="python:3.12-slim",
)

# Only these remote hosts may be cloned to keep the sandbox from hitting
# internal networks (SSRF hardening).
ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "gitea.com"}

PYTHON_FILE_RE = re.compile(r"^[a-zA-Z0-9_]+\.py$")

_IS_UNIX = platform.system() != "Windows"

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
        from app.services.ssrf import validate_url_for_clone

        validate_url_for_clone(url)
        workspace = Path(settings.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        project_dir = Path(tempfile.mkdtemp(prefix="omnimigrate_", dir=workspace))

        def _build(branch: str | None, extra: list[str] | None, target: str) -> list[str]:
            cmd = ["git", "clone", "--depth", str(depth)]
            if branch:
                cmd += ["--branch", branch]
            if extra:
                cmd += extra
            return [*cmd, url, target]

        branch_label: str | None = branch or None
        try:
            cls._run(
                _build(branch_label, extra_args, str(project_dir)),
                cwd=workspace,
                timeout=settings.git_clone_timeout_seconds,
            )
        except GitOperationError as exc:
            # The requested branch may not exist (e.g. the repo's default is
            # `master`, not `main`). Fall back to cloning without --branch so git
            # checks out the repository's default branch instead of failing.
            if branch_label:
                logger.warning(
                    "Branch %s not found for %s, falling back to default branch", branch_label, url
                )
                try:
                    cls._run(
                        _build(None, extra_args, str(project_dir)),
                        cwd=workspace,
                        timeout=settings.git_clone_timeout_seconds,
                    )
                except GitOperationError as exc2:
                    shutil.rmtree(project_dir, ignore_errors=True)
                    raise GitOperationError(f"Failed to clone {url}: {exc2}") from exc2
            else:
                shutil.rmtree(project_dir, ignore_errors=True)
                raise GitOperationError(f"Failed to clone {url}: {exc}") from exc

        size = cls._dir_size(project_dir)
        if size > settings.git_max_repo_bytes:
            shutil.rmtree(project_dir, ignore_errors=True)
            raise GitOperationError(
                f"Repository exceeds the {settings.git_max_repo_bytes // (1024 * 1024)} MB limit."
            )
        logger.info(
            "Cloned %s (%s) in %.2f MB",
            url,
            branch_label or "default",
            size / (1024 * 1024),
        )
        return str(project_dir)

    @classmethod
    def run_tests(cls, project_dir: str) -> TestRunResult:
        """Run the repo's pytest suite in an isolated Docker container."""
        # First, detect if there's a requirements.txt or pyproject.toml
        project_path = Path(project_dir)
        requirements_files = list(project_path.glob("requirements*.txt"))
        pyproject = project_path / "pyproject.toml"

        # Build a test script that installs deps and runs pytest
        test_script = f"""
import subprocess
import sys
import os

os.chdir("{project_dir}")

# Install dependencies if present
if os.path.exists("requirements.txt"):
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=False)
elif os.path.exists("pyproject.toml"):
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=False)

# Run pytest
result = subprocess.run(
    [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
    capture_output=True,
    text=True,
    timeout={settings.git_test_timeout_seconds}
)
print("__EXIT_CODE__", result.returncode)
print("__STDOUT__", result.stdout)
print("__STDERR__", result.stderr)
"""

        # Use dynamic sandbox to run tests
        result = _git_sandbox.verify_with_deps(test_script, language="python")

        # Parse output
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        
        exit_code = 1
        for line in stdout.splitlines():
            if line.startswith("__EXIT_CODE__"):
                try:
                    exit_code = int(line.split("__EXIT_CODE__")[1].strip())
                except Exception:
                    pass

        # Exit code 5 means "no tests collected"
        success = exit_code in (0, 5)

        return TestRunResult(
            returncode=exit_code,
            success=success,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=0,  # Duration tracked by sandbox
        )

    @staticmethod
    def cleanup(project_dir: str) -> None:
        """Best-effort removal of a sandbox clone."""
        try:
            shutil.rmtree(project_dir, ignore_errors=True)
        except Exception:
            logger.warning("Failed to remove sandbox %s", project_dir)

    # --- Branch introspection ---------------------------------------------

    @staticmethod
    def current_branches(project_dir: str) -> list[str]:
        """Local branch names in the checkout (with an optional `origin/` prefix)."""
        try:
            proc = subprocess.run(
                ["git", "branch", "--list", "--format", "%(refname:short)"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        return [b.strip() for b in (proc.stdout or "").splitlines() if b.strip()]

    @staticmethod
    def default_branch(project_dir: str) -> str:
        """The currently checked-out branch (what `git clone` checked out by default)."""
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "main"
        branch = (proc.stdout or "").strip()
        return branch or "main"

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
    def _sandbox_preexec() -> None:
        """Apply resource limits to child processes (Unix only)."""
        if platform.system() == "Windows":
            return
        try:
            import importlib

            _res = importlib.import_module("resource")
            _res.setrlimit(_res.RLIMIT_AS, (1_073_741_824, 1_073_741_824))
            _res.setrlimit(_res.RLIMIT_CPU, (60, 60))
            _res.setrlimit(_res.RLIMIT_NOFILE, (256, 256))
            _res.setrlimit(_res.RLIMIT_CORE, (0, 0))
        except (ValueError, OSError):
            pass

    @staticmethod
    def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=GitSandboxService._sandbox_preexec if _IS_UNIX else None,
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
