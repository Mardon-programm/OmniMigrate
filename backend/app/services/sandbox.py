from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class VerificationResult:
    success: bool
    syntax_ok: bool
    runtime_ok: bool
    errors: list[str] = field(default_factory=list)
    stdout: str = ""


class SandboxError(Exception):
    """Raised when the sandbox itself cannot be provisioned."""


class CodeSandbox:
    """Isolated verification environment for migrated code.

    Primary gate is a `compile()` syntax check; when enabled, the code is also
    executed in a constrained subprocess to catch runtime defects (with a
    timeout and a minimal environment).
    """

    def __init__(self, timeout: int | None = None, enabled: bool | None = None) -> None:
        self.timeout = timeout or settings.sandbox_timeout_seconds
        self.enabled = settings.sandbox_enabled if enabled is None else enabled

    def verify(self, code: str, language: str = "python") -> VerificationResult:
        if language == "python":
            return self._verify_python(code)
        return self._verify_generic(code)

    def _verify_python(self, code: str) -> VerificationResult:
        errors: list[str] = []

        # 1. Syntax gate.
        syntax_ok = True
        try:
            compile(code, "<omnimigrate-output>", "exec")
        except (SyntaxError, ValueError, TypeError) as exc:
            syntax_ok = False
            errors.append(f"SyntaxError: {exc}")

        if not syntax_ok:
            return VerificationResult(
                success=False, syntax_ok=False, runtime_ok=False, errors=errors
            )

        # 2. Runtime gate (best effort).
        if not self.enabled:
            return VerificationResult(
                success=True, syntax_ok=True, runtime_ok=True, errors=[]
            )

        runtime_ok, runtime_error, stdout = self._execute(code)
        if not runtime_ok:
            errors.append(runtime_error)
        return VerificationResult(
            success=runtime_ok,
            syntax_ok=True,
            runtime_ok=runtime_ok,
            errors=errors,
            stdout=stdout,
        )

    def _execute(self, code: str) -> tuple[bool, str, str]:
        """Execute the code in a subprocess with a strict timeout."""
        fd, path = tempfile.mkstemp(prefix="omnimigrate_sandbox_", suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(code)

            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONIOENCODING": "utf-8",
                "HOME": "/tmp",
            }
            python = os.environ.get("OMNIMIGRATE_SANDBOX_PYTHON", sys.executable)
            try:
                result = subprocess.run(
                    [python, path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                    cwd=tempfile.gettempdir(),
                )
            except subprocess.TimeoutExpired:
                return False, f"RuntimeError: sandbox execution timed out after {self.timeout}s", ""
            except FileNotFoundError as exc:
                return False, f"SandboxError: interpreter not found: {exc}", ""

            if result.returncode != 0:
                return (
                    False,
                    result.stderr.strip() or f"Process exited with code {result.returncode}",
                    result.stdout,
                )
            return True, "", result.stdout
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

    @staticmethod
    def _verify_generic(code: str) -> VerificationResult:
        """Non-Python targets: lightweight structural sanity checks."""
        errors: list[str] = []
        if not code or not code.strip():
            errors.append("Output is empty.")
        # Balanced braces heuristic for C-family languages.
        if code.count("{") != code.count("}"):
            errors.append("Unbalanced braces detected.")
        return VerificationResult(
            success=not errors,
            syntax_ok=not errors,
            runtime_ok=True,
            errors=errors,
        )


def check_syntax(code: str) -> tuple[bool, str | None]:
    """Quick syntax-only check (no subprocess)."""
    try:
        compile(code, "<omnimigrate-output>", "exec")
        return True, None
    except (SyntaxError, ValueError, TypeError) as exc:
        return False, f"{exc.__class__.__name__}: {exc}"
