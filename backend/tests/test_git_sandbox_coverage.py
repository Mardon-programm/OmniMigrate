"""Tests targeting uncovered lines in app/services/git_sandbox.py."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.services.git_sandbox import (
    GitOperationError,
    GitSandboxService,
    TestRunResult,
)


class TestRunResultSummary:
    def test_failure_summary_truncates_output(self):
        long_stderr = "\n".join(f"line {i}" for i in range(100))
        result = TestRunResult(
            returncode=1,
            success=False,
            stdout="",
            stderr=long_stderr,
            duration_seconds=1.2,
        )
        summary = result.summary()
        assert summary.startswith("Tests failed:")
        assert len(summary) <= 2000 + len("Tests failed: ")

    def test_failure_summary_from_stdout_when_stderr_empty(self):
        result = TestRunResult(
            returncode=1,
            success=False,
            stdout="FAILED test_foo.py::test_bar",
            stderr="",
            duration_seconds=0.5,
        )
        summary = result.summary()
        assert "FAILED test_foo.py::test_bar" in summary

    def test_failure_summary_uses_stdout_when_present(self):
        result = TestRunResult(
            returncode=1,
            success=False,
            stdout="stdout line",
            stderr="stderr line",
            duration_seconds=0.1,
        )
        summary = result.summary()
        assert "stdout line" in summary

    def test_failure_summary_falls_back_to_stderr(self):
        result = TestRunResult(
            returncode=1,
            success=False,
            stdout="",
            stderr="stderr line",
            duration_seconds=0.1,
        )
        summary = result.summary()
        assert "stderr line" in summary


class TestValidateRepoUrlEmpty:
    def test_empty_string_raises(self):
        with pytest.raises(GitOperationError, match="repo_url is required"):
            GitSandboxService.validate_repo_url("")

    def test_whitespace_only_raises(self):
        with pytest.raises(GitOperationError, match="repo_url is required"):
            GitSandboxService.validate_repo_url("   ")


class TestCloneRepository:
    def test_clone_success(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(
                workspace_root=str(tmp_path),
                git_clone_timeout_seconds=30,
                git_max_repo_bytes=1024 * 1024 * 100,
            ),
        )

        def fake_run(cmd, cwd, timeout):
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            (target / "dummy.py").write_text("x=1\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(GitSandboxService, "_run", staticmethod(fake_run))

        result = GitSandboxService.clone_repository(
            "https://github.com/owner/repo.git",
            branch="main",
            depth=1,
        )
        assert Path(result).is_dir()

    def test_clone_failure_cleans_up(self, monkeypatch, tmp_path):
        created_dirs = []
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(
                workspace_root=str(tmp_path),
                git_clone_timeout_seconds=30,
                git_max_repo_bytes=1024 * 1024 * 100,
            ),
        )

        def fake_run(cmd, cwd, timeout):
            target = Path(cmd[-1])
            created_dirs.append(str(target))
            target.mkdir(parents=True, exist_ok=True)
            raise GitOperationError("clone failed")

        monkeypatch.setattr(GitSandboxService, "_run", staticmethod(fake_run))

        with pytest.raises(GitOperationError, match="Failed to clone"):
            GitSandboxService.clone_repository("https://github.com/owner/repo.git")
        if created_dirs:
            assert not Path(created_dirs[0]).exists()

    def test_clone_size_limit_exceeded(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(
                workspace_root=str(tmp_path),
                git_clone_timeout_seconds=30,
                git_max_repo_bytes=10,
            ),
        )

        def fake_run(cmd, cwd, timeout):
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            (target / "big.bin").write_bytes(b"x" * 100)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(GitSandboxService, "_run", staticmethod(fake_run))

        with pytest.raises(GitOperationError, match="exceeds"):
            GitSandboxService.clone_repository("https://github.com/owner/repo.git")

    def test_clone_with_extra_args(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(
                workspace_root=str(tmp_path),
                git_clone_timeout_seconds=30,
                git_max_repo_bytes=1024 * 1024 * 100,
            ),
        )
        captured_cmds = []

        def fake_run(cmd, cwd, timeout):
            captured_cmds.append(list(cmd))
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            "app.services.git_sandbox.GitSandboxService._run",
            staticmethod(fake_run),
        )

        GitSandboxService.clone_repository(
            "https://github.com/owner/repo.git",
            extra_args=["--config", "core.sparseCheckout=true"],
        )
        assert "--config" in captured_cmds[0]


class TestRunTestsEdgeCases:
    def test_timeout_raises_git_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(git_test_timeout_seconds=1),
        )

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=1)

        monkeypatch.setattr("app.services.git_sandbox.subprocess.run", fake_run)

        with pytest.raises(GitOperationError, match="timed out"):
            GitSandboxService.run_tests(str(tmp_path))

    def test_file_not_found_raises_git_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "app.services.git_sandbox.settings",
            SimpleNamespace(git_test_timeout_seconds=60),
        )

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("pytest not found")

        monkeypatch.setattr("app.services.git_sandbox.subprocess.run", fake_run)

        with pytest.raises(GitOperationError, match="pytest is not available"):
            GitSandboxService.run_tests(str(tmp_path))


class TestCleanup:
    def test_cleanup_logs_on_exception(self, monkeypatch, tmp_path, caplog):
        import logging

        def fake_rmtree(path, ignore_errors=False):
            raise PermissionError("denied")

        monkeypatch.setattr("app.services.git_sandbox.shutil.rmtree", fake_rmtree)

        with caplog.at_level(logging.WARNING):
            GitSandboxService.cleanup(str(tmp_path / "nonexistent"))
        assert "Failed to remove sandbox" in caplog.text


class TestProcessDirectoryEdgeCases:
    def test_skips_unreadable_files(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_bytes(b"\x80\x81\x82")

        changes = GitSandboxService.process_directory(str(tmp_path), lambda code, rule: code, "")
        assert changes == []

    def test_skips_oserror_files(self, monkeypatch, tmp_path):
        f = tmp_path / "normal.py"
        f.write_text("x=1\n", encoding="utf-8")

        original_read_text = Path.read_text

        def bad_read(self, *a, **kw):
            if self.name == "normal.py":
                raise OSError("permission denied")
            return original_read_text(self, *a, **kw)

        monkeypatch.setattr(Path, "read_text", bad_read)
        changes = GitSandboxService.process_directory(str(tmp_path), lambda code, rule: code, "")
        assert changes == []

    def test_refactor_exception_skips_file(self, tmp_path):
        (tmp_path / "boom.py").write_text("x=1\n", encoding="utf-8")

        def bad_refactor(code, rule):
            raise ValueError("refactor exploded")

        changes = GitSandboxService.process_directory(str(tmp_path), bad_refactor, "")
        assert changes == []


class TestHealCodeEdgeCases:
    def test_read_error_skips_file(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x=1\n", encoding="utf-8")
        error_output = f'File "{f}", line 1\nNameError'

        from unittest.mock import patch

        original_read_text = Path.read_text

        def bad_read(self, *a, **kw):
            if self.name == "target.py":
                raise OSError("denied")
            return original_read_text(self, *a, **kw)

        with patch.object(Path, "read_text", bad_read):
            changes = GitSandboxService.heal_code_with_error(
                str(tmp_path), error_output, lambda b, e, r: b, ""
            )
        assert changes == []

    def test_heal_fn_exception_skips_file(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x=1\n", encoding="utf-8")
        error_output = f'File "{f}", line 1\nNameError'

        def bad_heal(broken, error, rule):
            raise RuntimeError("heal exploded")

        changes = GitSandboxService.heal_code_with_error(str(tmp_path), error_output, bad_heal, "")
        assert changes == []


class TestFilesFromError:
    def test_relative_path_in_error(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("x=1\n", encoding="utf-8")
        error_output = 'File "src/mod.py", line 1\nNameError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert "src/mod.py" in files

    def test_relative_path_not_found_ignored(self, tmp_path):
        error_output = 'File "does/not/exist.py", line 1\nNameError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert files == []

    def test_absolute_path_outside_root_ignored(self, tmp_path):
        error_output = 'File "/etc/passwd", line 1\nError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert files == []

    def test_absolute_path_inside_root(self, tmp_path):
        (tmp_path / "inside.py").write_text("x=1\n", encoding="utf-8")
        error_output = f'File "{tmp_path / "inside.py"}", line 1\nError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert "inside.py" in files

    def test_oserror_on_resolve_ignored(self, tmp_path):
        error_output = 'File "/nonexistent/magic.py", line 1\nError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert files == []

    def test_backslash_relative_path(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("y=2\n", encoding="utf-8")
        error_output = 'File "tests\\test_x.py", line 1\nNameError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert "tests/test_x.py" in files

    def test_deduplicates_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
        a_path = tmp_path / "a.py"
        error_output = f'File "{a_path}", line 1\nNameError\n' f'File "{a_path}", line 2\nNameError'
        files = GitSandboxService._files_from_error(str(tmp_path), error_output)
        assert files.count("a.py") == 1


class TestRun:
    def test_timeout_raises(self, monkeypatch):
        def fake_subprocess_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr("app.services.git_sandbox.subprocess.run", fake_subprocess_run)

        with pytest.raises(GitOperationError, match="timed out"):
            GitSandboxService._run(["git", "clone"], Path("."), timeout=5)

    def test_nonzero_returncode_raises(self, monkeypatch):
        def fake_subprocess_run(*args, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="fatal: not found")

        monkeypatch.setattr("app.services.git_sandbox.subprocess.run", fake_subprocess_run)

        with pytest.raises(GitOperationError, match="Command failed"):
            GitSandboxService._run(["git", "bad"], Path("."), timeout=5)

    def test_success_returns_completed(self, monkeypatch):
        expected = SimpleNamespace(returncode=0, stdout="ok", stderr="")

        def fake_subprocess_run(*args, **kwargs):
            return expected

        monkeypatch.setattr("app.services.git_sandbox.subprocess.run", fake_subprocess_run)

        result = GitSandboxService._run(["git", "status"], Path("."), timeout=5)
        assert result is expected


class TestDirSize:
    def test_empty_dir(self, tmp_path):
        assert GitSandboxService._dir_size(tmp_path) == 0

    def test_sums_files(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"hello")
        (tmp_path / "b.txt").write_bytes(b"world!")
        assert GitSandboxService._dir_size(tmp_path) == 11

    def test_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_bytes(b"data")
        assert GitSandboxService._dir_size(tmp_path) == 4

    def test_oserror_on_stat_continues(self, monkeypatch, tmp_path):
        (tmp_path / "good.txt").write_bytes(b"ok")
        (tmp_path / "bad.txt").write_bytes(b"no")

        real_is_file = Path.is_file

        def mock_is_file(self):
            if self.name == "bad.txt":
                return True
            return real_is_file(self)

        original_stat = Path.stat

        def mock_stat(self, **kw):
            if self.name == "bad.txt":
                raise OSError("cannot stat")
            return original_stat(self, **kw)

        monkeypatch.setattr(Path, "is_file", mock_is_file)
        monkeypatch.setattr(Path, "stat", mock_stat)
        size = GitSandboxService._dir_size(tmp_path)
        assert size == 2

    def test_ignores_directories(self, tmp_path):
        sub = tmp_path / "dir"
        sub.mkdir()
        (tmp_path / "file.txt").write_bytes(b"x")
        assert GitSandboxService._dir_size(tmp_path) == 1
