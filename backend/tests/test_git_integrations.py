import subprocess
import tempfile
from pathlib import Path

import pytest
from app.services.git_integrations import GitHubIntegrationService


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_remote():
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        remote.mkdir()
        _git(remote, "init", "--bare")
        yield str(remote)


@pytest.fixture()
def local_remote():
    yield from _make_remote()


@pytest.fixture()
def worktree():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "T")
        (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")
        _git(repo, "remote", "add", "origin", "https://github.com/fake/fake.git")
        yield repo


class TestCommitAndPush:
    def test_commits_and_pushes(self, worktree, local_remote):
        (worktree / "app.py").write_text("print('hello world')\n", encoding="utf-8")

        result = GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="fake-token",
            repo_owner="fake",
            repo_name="fake",
            branch_name="omnimigrate/test",
            commit_message="refactor: test push",
            remote_url=local_remote,
        )

        assert result == local_remote
        # Branch must exist on the remote.
        out = subprocess.run(
            ["git", "ls-remote", "--heads", local_remote],
            capture_output=True,
            text=True,
        ).stdout
        assert "omnimigrate/test" in out

    def test_remote_url_is_restored_without_token(self, worktree, local_remote):
        (worktree / "app.py").write_text("print('bye')\n", encoding="utf-8")
        GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="secret-token",
            repo_owner="fake",
            repo_name="fake",
            branch_name="omnimigrate/test",
            commit_message="refactor: test push",
            remote_url=local_remote,
        )
        out = _git(worktree, "remote", "get-url", "origin")
        assert out.stdout.strip() == local_remote
        assert "secret-token" not in out.stdout
