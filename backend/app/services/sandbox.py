from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import docker
from docker.errors import DockerException, ImageNotFound

from app.core.config import settings


@dataclass
class VerificationResult:
    success: bool
    syntax_ok: bool
    runtime_ok: bool
    errors: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout_seconds: int = 30
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_disabled: bool = True
    read_only_rootfs: bool = True
    pids_limit: int = 64
    tmpfs_size: str = "64m"


class SandboxError(Exception):
    """Raised when the sandbox itself cannot be provisioned."""
    pass


class DockerSandbox:
    """
    Docker-based isolated code execution sandbox.
    
    Security features:
    - Runs in ephemeral container with no network access
    - Read-only root filesystem
    - Memory/CPU/pid limits
    - Non-root user
    - Automatic cleanup after execution
    - No access to host filesystem except mounted temp dir
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        enabled: bool = True,
        image: str = "python:3.12-slim",
    ):
        self.config = config or SandboxConfig()
        self.enabled = enabled and settings.sandbox_enabled
        self.image = image
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except DockerException as e:
                raise SandboxError(f"Docker not available: {e}")
        return self._client

    def _ensure_image(self) -> None:
        """Pull sandbox image if not present."""
        try:
            self.client.images.get(self.image)
        except ImageNotFound:
            try:
                self.client.images.pull(self.image)
            except DockerException as e:
                raise SandboxError(f"Failed to pull sandbox image {self.image}: {e}")

    def _create_container_config(self, code: str, workdir: str, entrypoint: list[str]) -> dict:
        """Create secure container configuration."""
        return {
            "image": self.image,
            "command": entrypoint,
            "working_dir": workdir,
            "volumes": {
                workdir: {"bind": workdir, "mode": "ro"},
            },
            "environment": {
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                "HOME": "/tmp",
            },
            "user": "1000:1000",  # Non-root user
            "mem_limit": self.config.memory_limit,
            "cpu_quota": int(self.config.cpu_limit * 100000),
            "cpu_period": 100000,
            "pids_limit": self.config.pids_limit,
            "network_mode": "none" if self.config.network_disabled else "bridge",
            "read_only": self.config.read_only_rootfs,
            "tmpfs": {"/tmp": f"size={self.config.tmpfs_size},exec"} if self.config.read_only_rootfs else None,
            "security_opt": ["no-new-privileges:true"],
            "cap_drop": ["ALL"],
            "detach": False,
            "auto_remove": True,
        }

    def verify(self, code: str, language: str = "python") -> VerificationResult:
        """Verify code syntax and optionally execute in isolated container."""
        if language == "python":
            return self._verify_python(code)
        return self._verify_generic(code)

    def _verify_python(self, code: str) -> VerificationResult:
        errors: list[str] = []

        # 1. Syntax gate (fast, no container needed)
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

        # 2. Runtime gate in isolated container
        if not self.enabled:
            return VerificationResult(success=True, syntax_ok=True, runtime_ok=True, errors=[])

        try:
            self._ensure_image()
            return self._execute_in_container(code)
        except SandboxError as e:
            return VerificationResult(
                success=False,
                syntax_ok=True,
                runtime_ok=False,
                errors=[f"SandboxError: {e}"],
            )

    def _execute_in_container(self, code: str) -> VerificationResult:
        """Execute code in ephemeral Docker container."""
        with tempfile.TemporaryDirectory(prefix="omnimigrate_sandbox_") as tmpdir:
            workdir = Path(tmpdir)
            code_file = workdir / "script.py"
            code_file.write_text(code, encoding="utf-8")

            container_config = self._create_container_config(
                code=code,
                workdir=str(workdir),
                entrypoint=["python", "script.py"],
            )

            try:
                container = self.client.containers.run(
                    **container_config,
                    stdout=True,
                    stderr=True,
                )
                stdout = container.decode("utf-8") if isinstance(container, bytes) else container
                return VerificationResult(
                    success=True,
                    syntax_ok=True,
                    runtime_ok=True,
                    errors=[],
                    stdout=stdout,
                )
            except docker.errors.ContainerError as e:
                stderr = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else str(e.stderr)
                return VerificationResult(
                    success=False,
                    syntax_ok=True,
                    runtime_ok=False,
                    errors=[stderr.strip() or f"Process exited with code {e.exit_status}"],
                    stdout=e.stdout.decode("utf-8") if e.stdout else "",
                    stderr=stderr,
                )
            except docker.errors.ImageNotFound:
                raise SandboxError(f"Image {self.image} not found")
            except docker.errors.APIError as e:
                raise SandboxError(f"Docker API error: {e}")

    @staticmethod
    def _verify_generic(code: str) -> VerificationResult:
        """Non-Python targets: lightweight structural sanity checks."""
        errors: list[str] = []
        if not code or not code.strip():
            errors.append("Output is empty.")
        if code.count("{") != code.count("}"):
            errors.append("Unbalanced braces detected.")
        return VerificationResult(
            success=not errors,
            syntax_ok=not errors,
            runtime_ok=True,
            errors=errors,
        )


class E2BSandbox:
    """
    E2B (e2b.dev) sandbox integration for cloud-based isolated execution.
    
    Provides:
    - True cloud isolation (Firecracker microVMs)
    - Pre-installed Python + common ML/data science packages
    - Persistent sessions for multi-step workflows
    - File upload/download support
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key or os.getenv("E2B_API_KEY")
        self.timeout = timeout
        self._session_id: Optional[str] = None

    async def _get_session(self):
        """Get or create E2B session."""
        if not self.api_key:
            raise SandboxError("E2B_API_KEY not configured")

        try:
            import e2b
        except ImportError:
            raise SandboxError("e2b package not installed. Run: pip install e2b")

        if self._session_id is None:
            self._session_id = await e2b.Session.create_async(
                api_key=self.api_key,
                id="python3",
                timeout=self.timeout,
            )
        return self._session_id

    async def verify(self, code: str, language: str = "python") -> VerificationResult:
        if language != "python":
            return DockerSandbox._verify_generic(code)

        # Syntax check first
        try:
            compile(code, "<omnimigrate-output>", "exec")
        except (SyntaxError, ValueError, TypeError) as exc:
            return VerificationResult(
                success=False, syntax_ok=False, runtime_ok=False, errors=[f"SyntaxError: {exc}"]
            )

        if not self.api_key:
            return VerificationResult(success=True, syntax_ok=True, runtime_ok=True, errors=[])

        try:
            import e2b
            session = await e2b.Session.connect_async(self._session_id)
            
            # Execute code
            result = await session.run_python_async(code)
            
            return VerificationResult(
                success=result.error is None,
                syntax_ok=True,
                runtime_ok=result.error is None,
                errors=[result.error] if result.error else [],
                stdout=result.logs.stdout,
                stderr=result.logs.stderr,
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                syntax_ok=True,
                runtime_ok=False,
                errors=[f"E2B execution error: {e}"],
            )

    async def close(self):
        """Close the E2B session."""
        if self._session_id:
            try:
                import e2b
                session = await e2b.Session.connect_async(self._session_id)
                await session.close_async()
            except Exception:
                pass
            self._session_id = None


class ModalSandbox:
    """
    Modal (modal.com) sandbox integration for serverless GPU/CPU execution.
    
    Features:
    - Serverless containers with cold start ~1s
    - GPU support for ML workloads
    - Automatic scaling
    - Pay-per-second billing
    """

    def __init__(self, token_id: Optional[str] = None, token_secret: Optional[str] = None):
        self.token_id = token_id or os.getenv("MODAL_TOKEN_ID")
        self.token_secret = token_secret or os.getenv("MODAL_TOKEN_SECRET")
        self._stub = None

    def _get_stub(self):
        """Get or create Modal stub."""
        if self._stub is None:
            try:
                import modal
            except ImportError:
                raise SandboxError("modal package not installed. Run: pip install modal")

            if not self.token_id or not self.token_secret:
                raise SandboxError("MODAL_TOKEN_ID and MODAL_TOKEN_SECRET not configured")

            # Create a stub with a sandbox function
            self._stub = modal.Stub("omnimigrate-sandbox")
            
            @self._stub.function(
                image=modal.Image.debian_slim().pip_install(),
                timeout=60,
                cpu=1.0,
                memory=512,
            )
            def run_python(code: str):
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    f.flush()
                    try:
                        result = subprocess.run(
                            ['python', f.name],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        return {
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'returncode': result.returncode,
                        }
                    finally:
                        os.unlink(f.name)

        return self._stub

    async def verify(self, code: str, language: str = "python") -> VerificationResult:
        if language != "python":
            return DockerSandbox._verify_generic(code)

        try:
            compile(code, "<omnimigrate-output>", "exec")
        except (SyntaxError, ValueError, TypeError) as exc:
            return VerificationResult(
                success=False, syntax_ok=False, runtime_ok=False, errors=[f"SyntaxError: {exc}"]
            )

        if not self.token_id:
            return VerificationResult(success=True, syntax_ok=True, runtime_ok=True, errors=[])

        try:
            import modal
            stub = self._get_stub()
            
            with stub.run():
                run_python = stub["run_python"]
                result = await run_python.remote.aio(code)
            
            return VerificationResult(
                success=result['returncode'] == 0,
                syntax_ok=True,
                runtime_ok=result['returncode'] == 0,
                errors=[result['stderr']] if result['returncode'] != 0 else [],
                stdout=result['stdout'],
                stderr=result['stderr'],
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                syntax_ok=True,
                runtime_ok=False,
                errors=[f"Modal execution error: {e}"],
            )


class SandboxFactory:
    """Factory for creating appropriate sandbox based on environment."""

    @staticmethod
    def create(
        sandbox_type: str = "auto",
        **kwargs
    ) -> "DockerSandbox | E2BSandbox | ModalSandbox":
        """
        Create sandbox instance.
        
        Args:
            sandbox_type: "docker", "e2b", "modal", or "auto"
            **kwargs: Passed to sandbox constructor
        """
        if sandbox_type == "docker":
            return DockerSandbox(**kwargs)
        elif sandbox_type == "e2b":
            return E2BSandbox(**kwargs)
        elif sandbox_type == "modal":
            return ModalSandbox(**kwargs)
        elif sandbox_type == "auto":
            # Prefer Docker if available, fallback to local
            try:
                client = docker.from_env()
                client.ping()
                return DockerSandbox(**kwargs)
            except Exception:
                # Fallback to local subprocess (dev only)
                from app.services.sandbox import CodeSandbox
                return CodeSandbox(**kwargs)
        else:
            raise ValueError(f"Unknown sandbox type: {sandbox_type}")


# Backward compatibility - use Docker sandbox as default
CodeSandbox = DockerSandbox


def check_syntax(code: str) -> tuple[bool, str | None]:
    """Quick syntax-only check (no subprocess)."""
    try:
        compile(code, "<omnimigrate-output>", "exec")
        return True, None
    except (SyntaxError, ValueError, TypeError) as exc:
        return False, f"{exc.__class__.__name__}: {exc}"