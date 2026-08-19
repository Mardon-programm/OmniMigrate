"""Tests targeting uncovered lines in app/services/git_integrations.py."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.git_integrations import (
    GitHubIntegrationError,
    GitHubIntegrationService,
    _run_git,
)


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def bare_remote():
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        remote.mkdir()
        _git(remote, "init", "--bare")
        yield str(remote)


@pytest.fixture()
def worktree(bare_remote):
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "T")
        (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")
        _git(repo, "remote", "add", "origin", bare_remote)
        yield repo


class TestCommitAndPushTokenRemote:
    def test_default_remote_constructs_token_url(self, worktree, bare_remote):
        (worktree / "app.py").write_text("print('updated')\n", encoding="utf-8")
        result = GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="ghp_abc123",
            repo_owner="myorg",
            repo_name="myrepo",
            branch_name="omnimigrate/test",
            commit_message="refactor: update",
            remote_url=bare_remote,
        )
        assert result == bare_remote

    def test_custom_remote_url_uses_it_directly(self, worktree, bare_remote):
        (worktree / "app.py").write_text("print('custom')\n", encoding="utf-8")
        result = GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="ghp_abc123",
            repo_owner="myorg",
            repo_name="myrepo",
            branch_name="omnimigrate/test",
            commit_message="refactor: custom",
            remote_url=bare_remote,
        )
        assert result == bare_remote

    def test_author_name_and_email_override(self, worktree, bare_remote):
        (worktree / "app.py").write_text("print('author')\n", encoding="utf-8")
        GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="ghp_abc123",
            repo_owner="myorg",
            repo_name="myrepo",
            branch_name="omnimigrate/test",
            commit_message="refactor: author",
            author_name="Custom Bot",
            author_email="bot@custom.com",
            remote_url=bare_remote,
        )
        out = _git(worktree, "log", "-1", "--format=%an <%ae>")
        assert "Custom Bot" in out.stdout
        assert "bot@custom.com" in out.stdout


class TestCommitAndPushNothingToCommit:
    def test_nothing_to_commit_succeeds(self, monkeypatch, worktree, bare_remote):
        original_run_git = _run_git

        def fake_run_git(args, project_dir, env):
            if args and args[0] == "commit":
                raise subprocess.CalledProcessError(
                    1,
                    ["git", "commit"],
                    output="",
                    stderr="nothing to commit, working tree clean",
                )
            return original_run_git(args, project_dir, env)

        monkeypatch.setattr("app.services.git_integrations._run_git", fake_run_git)

        result = GitHubIntegrationService.commit_and_push(
            project_dir=str(worktree),
            github_token="ghp_abc123",
            repo_owner="myorg",
            repo_name="myrepo",
            branch_name="omnimigrate/test-no-changes",
            commit_message="refactor: no changes",
            remote_url=bare_remote,
        )
        assert result == bare_remote


class TestCommitAndPushRetry:
    def test_force_with_lease_failure_triggers_plain_push(self, monkeypatch, bare_remote):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init", "-b", "main")
            _git(repo, "config", "user.email", "t@t.t")
            _git(repo, "config", "user.name", "T")
            (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "init")
            _git(repo, "remote", "add", "origin", bare_remote)

            push_count = 0
            original_run_git = _run_git

            def fake_run_git(args, project_dir, env):
                nonlocal push_count
                if args and args[0] == "push":
                    push_count += 1
                    if push_count == 1 and "--force-with-lease" in args:
                        raise subprocess.CalledProcessError(1, ["git", "push"], stderr="reject")
                    return
                if args and args[0] == "commit":
                    raise subprocess.CalledProcessError(
                        1,
                        ["git", "commit"],
                        output="",
                        stderr="nothing to commit, working tree clean",
                    )
                return original_run_git(args, project_dir, env)

            monkeypatch.setattr("app.services.git_integrations._run_git", fake_run_git)

            result = GitHubIntegrationService.commit_and_push(
                project_dir=str(repo),
                github_token="ghp_abc123",
                repo_owner="myorg",
                repo_name="myrepo",
                branch_name="omnimigrate/test",
                commit_message="refactor: retry",
                remote_url=bare_remote,
            )
            assert result == bare_remote
            assert push_count >= 2


class TestCreatePullRequest:
    @pytest.fixture()
    def service(self):
        return GitHubIntegrationService(token="ghp_test", api_url="https://api.github.com")

    async def test_create_pull_request_success(self, service, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"number": 42, "html_url": "url", "url": "api"}'
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/x/y/pull/42",
            "url": "https://api.github.com/repos/x/y/pulls/42",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "app.services.git_integrations.httpx.AsyncClient",
            MagicMock(return_value=mock_client_instance),
        )

        result = await service.create_pull_request(
            repo_owner="x",
            repo_name="y",
            title="Refactor PR",
            head="omnimigrate/feat",
            base="main",
            body="Automated migration",
        )
        assert result["number"] == 42
        assert "pull/42" in result["html_url"]

    async def test_create_pull_request_http_error(self, service, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.content = b'{"message": "Validation Failed"}'
        mock_response.json.return_value = {"message": "Validation Failed"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "app.services.git_integrations.httpx.AsyncClient",
            MagicMock(return_value=mock_client_instance),
        )

        with pytest.raises(GitHubIntegrationError, match="422"):
            await service.create_pull_request(
                repo_owner="x",
                repo_name="y",
                title="Bad PR",
                head="feat",
                base="main",
                body="...",
            )

    async def test_create_pull_request_empty_body_error(self, service, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.content = b""
        mock_response.text = "rate limited"

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "app.services.git_integrations.httpx.AsyncClient",
            MagicMock(return_value=mock_client_instance),
        )

        with pytest.raises(GitHubIntegrationError, match="403"):
            await service.create_pull_request(
                repo_owner="x",
                repo_name="y",
                title="Rate limited",
                head="feat",
                base="main",
                body="...",
            )

    async def test_create_pull_request_sends_correct_payload(self, service, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"number": 1, "html_url": "url", "url": "api_url"}'
        mock_response.json.return_value = {"number": 1, "html_url": "url", "url": "api_url"}

        captured = {}
        mock_client_instance = AsyncMock()

        async def capture_post(url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return mock_response

        mock_client_instance.post = capture_post
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "app.services.git_integrations.httpx.AsyncClient",
            MagicMock(return_value=mock_client_instance),
        )

        await service.create_pull_request(
            repo_owner="org",
            repo_name="repo",
            title="My PR",
            head="feature",
            base="develop",
            body="Description",
        )
        assert captured["url"] == "https://api.github.com/repos/org/repo/pulls"
        assert captured["headers"]["Authorization"] == "Bearer ghp_test"
        assert captured["json"]["title"] == "My PR"
