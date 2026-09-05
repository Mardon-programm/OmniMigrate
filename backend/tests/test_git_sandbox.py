import subprocess
import tempfile
from pathlib import Path

import pytest
from app.services.git_sandbox import (
    GitOperationError,
    GitSandboxService,
)


class TestRepoUrlValidation:
    def test_rejects_file_url(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.validate_repo_url("file:///etc/passwd")

    def test_rejects_local_path(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.validate_repo_url("C:\\repos\\legacy")

    def test_rejects_git_protocol(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.validate_repo_url("git://github.com/foo/bar.git")

    def test_rejects_unknown_host(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.validate_repo_url("https://internal.corp/foo/bar.git")

    def test_accepts_github_https(self):
        url = "https://github.com/psf/requests.git"
        assert GitSandboxService.validate_repo_url(url) == url

    def test_accepts_github_ssh(self):
        url = "git@github.com:psf/requests.git"
        assert GitSandboxService.validate_repo_url(url) == url


@pytest.fixture()
def sandbox_project():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def _git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def git_repo():
    """A local git repo committed to git with one legacy Python file."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "T")
        (repo / "legacy.py").write_text("def get(name):\n    return name\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")
        yield repo


class TestRunTests:
    def test_pass_on_green_suite(self, sandbox_project):
        (Path(sandbox_project) / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )
        result = GitSandboxService.run_tests(sandbox_project)
        assert result.success is True
        assert result.returncode == 0

    def test_fail_on_red_suite(self, sandbox_project):
        (Path(sandbox_project) / "test_bad.py").write_text(
            "def test_bad():\n    assert False\n", encoding="utf-8"
        )
        result = GitSandboxService.run_tests(sandbox_project)
        assert result.success is False
        assert "assert False" in result.stdout or "assert False" in result.stderr

    def test_green_when_no_tests_ran(self, sandbox_project):
        # A repo with no tests must not block the autonomous pipeline.
        (Path(sandbox_project) / "app.py").write_text("x = 1\n", encoding="utf-8")
        result = GitSandboxService.run_tests(sandbox_project)
        assert result.success is True


class TestProcessDirectory:
    def test_refactors_legacy_python(self, sandbox_project):
        (Path(sandbox_project) / "xrange_usage.py").write_text(
            "for i in xrange(3):\n    print(i)\n", encoding="utf-8"
        )
        changes = GitSandboxService.process_directory(
            sandbox_project,
            lambda code, rule: (
                __import__("app.services.rule_engine", fromlist=["x"])
                .apply_modernization_rules(code)
                .code
            ),
            "",
        )
        assert len(changes) == 1
        assert "range(3)" in changes[0].after
        assert changes[0].rel_path == "xrange_usage.py"

    def test_skips_excluded_dirs(self, sandbox_project):
        root = Path(sandbox_project)
        (root / ".venv").mkdir()
        (root / ".venv" / "xrange_usage.py").write_text(
            "for i in xrange(3):\n    pass\n", encoding="utf-8"
        )
        changes = GitSandboxService.process_directory(
            sandbox_project,
            lambda code, rule: (
                __import__("app.services.rule_engine", fromlist=["x"])
                .apply_modernization_rules(code)
                .code
            ),
            "",
        )
        assert changes == []


class TestHealCodeWithError:
    def test_extracts_affected_file(self, git_repo):
        error = (
            f'File "{git_repo}/legacy.py", line 1, in <module>\n'
            "NameError: name 'xrange' is not defined"
        )
        files = GitSandboxService._files_from_error(str(git_repo), error)
        assert files == ["legacy.py"]

    def test_heals_implicated_file(self, git_repo):
        (git_repo / "legacy.py").write_text("for i in xrange(3):\n    pass\n", encoding="utf-8")
        error = (
            f'File "{git_repo}/legacy.py", line 1, in <module>\n'
            "NameError: name 'xrange' is not defined"
        )

        def heal(code, err, rule):
            return (
                __import__("app.services.rule_engine", fromlist=["x"])
                .apply_modernization_rules(code)
                .code
            )

        changes = GitSandboxService.heal_code_with_error(str(git_repo), error, heal, "")
        assert any(c.rel_path == "legacy.py" for c in changes)


class TestClone:
    def test_clone_rejects_bad_url(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.clone_repository("file:///etc/passwd")
