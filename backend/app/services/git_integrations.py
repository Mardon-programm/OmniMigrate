from __future__ import annotations

import contextlib
import logging
import os
import subprocess

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubIntegrationError(RuntimeError):
    """Raised when a GitHub API call or git push fails."""


class GitHubIntegrationService:
    """Push refactored branches and open pull requests on GitHub."""

    def __init__(self, token: str, api_url: str | None = None) -> None:
        self.token = token
        self.api_url = (api_url or settings.github_api_url).rstrip("/")

    # --- Git push ----------------------------------------------------------

    @staticmethod
    def commit_and_push(
        project_dir: str,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        branch_name: str,
        commit_message: str,
        author_name: str | None = None,
        author_email: str | None = None,
        remote_url: str | None = None,
    ) -> str:
        """Commit all sandbox changes and push them to `branch_name`.

        Returns the push target URL on success. The token is only attached to
        the remote for the duration of the push and stripped afterwards so it
        is never left behind in the repo config.
        """
        remote = remote_url or f"https://github.com/{repo_owner}/{repo_name}.git"
        if remote_url:
            token_remote = remote_url
        else:
            token_remote = (
                f"https://x-access-token:{github_token}@github.com/{repo_owner}/{repo_name}.git"
            )
        name = author_name or settings.git_author_name
        email = author_email or settings.git_author_email

        env = {"GIT_TERMINAL_PROMPT": "0"}
        _run_git(["config", "user.name", name], project_dir, env)
        _run_git(["config", "user.email", email], project_dir, env)
        _run_git(["checkout", "-b", branch_name], project_dir, env)
        _run_git(["add", "-A"], project_dir, env)
        try:
            _run_git(["commit", "-m", commit_message], project_dir, env)
        except subprocess.CalledProcessError as exc:
            if "nothing to commit" in (exc.stderr or "").lower():
                logger.info("Nothing to commit for branch %s", branch_name)
            else:
                raise

        # Attach authenticated remote only for the push, then restore.
        _run_git(["remote", "set-url", "origin", token_remote], project_dir, env)
        try:
            _run_git(
                ["push", "-u", "origin", branch_name, "--force-with-lease"],
                project_dir,
                env,
            )
        except subprocess.CalledProcessError:
            # Re-push without lease to tolerate concurrent upstream activity.
            _run_git(["push", "-u", "origin", branch_name], project_dir, env)
        finally:
            _run_git(["remote", "set-url", "origin", remote], project_dir, env)
            with contextlib.suppress(subprocess.CalledProcessError):
                _run_git(["config", "--unset-all", "http.extraheader"], project_dir, env)
        return remote

    # --- Pull requests -----------------------------------------------------

    async def create_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        title: str,
        head: str,
        base: str,
        body: str,
    ) -> dict:
        """Open a GitHub pull request and return its number and html_url."""
        url = f"{self.api_url}/repos/{repo_owner}/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            detail = response.json().get("message", response.text) if response.content else ""
            raise GitHubIntegrationError(
                f"GitHub rejected the pull request ({response.status_code}): {detail}"
            )
        data = response.json()
        return {
            "number": data.get("number"),
            "html_url": data.get("html_url"),
            "url": data.get("url"),
        }


def _run_git(args: list[str], project_dir: str, env: dict) -> None:
    """Run a git subcommand inside the sandbox, raising on failure."""
    cmd = ["git", *args]
    proc = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=60,
    )
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr
        )
