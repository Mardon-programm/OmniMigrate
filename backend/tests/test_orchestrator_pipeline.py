import asyncio
import subprocess
import tempfile
from pathlib import Path

import pytest
from app.core.config import settings
from app.models import JobStatus, MigrationJob, Project
from app.services.git_integrations import GitHubIntegrationService
from app.services.git_sandbox import GitOperationError
from app.services.orchestrator import AutonomousMigrationOrchestrator
from app.services.token_encryption import encrypt_token
from tests.conftest import make_user


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def local_remote():
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        remote.mkdir()
        _git(remote, "init", "--bare")
        yield str(remote)


@pytest.fixture()
def legacy_repo(local_remote):
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "T")
        (repo / "legacy.py").write_text("for i in xrange(3):\n    print(i)\n", encoding="utf-8")
        (repo / "test_legacy.py").write_text(
            "def test_legacy():\n    assert True\n", encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")
        _git(repo, "remote", "add", "origin", local_remote)
        _git(repo, "push", "origin", "main")
        yield repo, local_remote


def _clone_from_local(repo_dir, bare_remote):
    """Run a clone from a local checkout so the allowlist SSRF guard is bypassed."""

    def _clone(repo_url, branch="main", depth=1, extra_args=None):
        workspace = Path(settings.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        dest = Path(tempfile.mkdtemp(prefix="omnimigrate_", dir=workspace))
        cmd = ["git", "clone", "--depth", str(depth), "--branch", branch, repo_dir, str(dest)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        _git(dest, "remote", "set-url", "origin", bare_remote)
        return str(dest)

    return _clone


@pytest.fixture()
def local_github(monkeypatch, legacy_repo):
    """Wire the pipeline to a local bare remote instead of real GitHub."""
    repo_dir, remote = legacy_repo
    real_commit = GitHubIntegrationService.commit_and_push

    def _commit(
        project_dir,
        token,
        owner,
        name,
        branch,
        message,
        author_name=None,
        author_email=None,
        remote_url=None,
    ):
        return real_commit(
            project_dir,
            token,
            owner,
            name,
            branch,
            message,
            author_name=author_name,
            author_email=author_email,
            remote_url=remote,
        )

    async def _fake_pr(self, owner, name, title, head, base, body):
        assert owner == "acme"
        assert name == "legacy"
        assert "Modernize" in title
        return {"html_url": "https://github.com/acme/legacy/pull/7", "number": 7}

    monkeypatch.setattr(
        "app.services.git_sandbox.GitSandboxService.clone_repository",
        _clone_from_local(repo_dir, remote),
    )
    monkeypatch.setattr(
        "app.services.git_integrations.GitHubIntegrationService.commit_and_push", _commit
    )
    monkeypatch.setattr(
        "app.services.git_integrations.GitHubIntegrationService.create_pull_request", _fake_pr
    )
    return remote


class TestFullPipeline:
    async def test_end_to_end(self, local_github):
        events = []

        async def progress(pct, stage, message):
            events.append((pct, stage))

        orchestrator = AutonomousMigrationOrchestrator(progress=progress)
        result = await orchestrator.execute_full_pipeline(
            repo_url=local_github,
            github_token="fake-token",
            repo_owner="acme",
            repo_name="legacy",
            context_rule=None,
            base_branch="main",
        )

        assert result.branch_name.startswith(settings.git_branch_prefix)
        assert result.pull_request_url == "https://github.com/acme/legacy/pull/7"
        assert result.pull_request_number == 7
        assert len(result.changed_files) == 1
        assert result.changed_files[0].rel_path == "legacy.py"
        assert "range(3)" in result.changed_files[0].after
        assert result.baseline_tests is not None and result.baseline_tests.success
        assert result.post_refactor_tests is not None and result.post_refactor_tests.success
        assert result.heal_attempts == 0
        assert result.diff_summary
        assert "clone" in [e[1] for e in events]
        assert "pr" in [e[1] for e in events]
        # Branch should exist on the remote.
        out = await asyncio.to_thread(
            subprocess.check_output, ["git", "ls-remote", "--heads", local_github], text=True
        )
        assert result.branch_name in out

    async def test_cleanup_on_failure(self, monkeypatch, legacy_repo):
        _repo_dir, remote = legacy_repo

        def _clone_fails(repo_url, branch="main", depth=1, extra_args=None):
            raise GitOperationError("clone failed")

        monkeypatch.setattr(
            "app.services.git_sandbox.GitSandboxService.clone_repository", _clone_fails
        )
        orchestrator = AutonomousMigrationOrchestrator()
        with pytest.raises(GitOperationError):
            await orchestrator.execute_full_pipeline(
                repo_url=remote,
                github_token="token",
                repo_owner="acme",
                repo_name="legacy",
            )

    async def test_fails_when_target_file_missing(self, local_github):
        """A typo'd target path must fail with a clear message, not silently skip."""
        orchestrator = AutonomousMigrationOrchestrator()
        with pytest.raises(GitOperationError) as exc_info:
            await orchestrator.execute_full_pipeline(
                repo_url=local_github,
                github_token="fake-token",
                repo_owner="acme",
                repo_name="legacy",
                base_branch="main",
                target_files=["does-not-exist.py"],
            )
        message = str(exc_info.value)
        assert "does-not-exist.py" in message
        assert "not found" in message

    async def test_succeeds_with_valid_target_file(self, local_github):
        """Migrating a file that does exist in the repo should still succeed."""
        orchestrator = AutonomousMigrationOrchestrator()
        result = await orchestrator.execute_full_pipeline(
            repo_url=local_github,
            github_token="fake-token",
            repo_owner="acme",
            repo_name="legacy",
            base_branch="main",
            target_files=["legacy.py"],
        )
        assert result.pull_request_url == "https://github.com/acme/legacy/pull/7"
        assert [c.rel_path for c in result.changed_files] == ["legacy.py"]

    async def test_fails_cleanly_when_nothing_to_migrate(self, monkeypatch, legacy_repo):
        """A repo with nothing modernizable must fail cleanly, not crash in git commit."""
        _repo_dir, remote = legacy_repo
        modern_dir = Path(legacy_repo[0]).parent / "modern"
        modern_dir.mkdir(exist_ok=True)
        (modern_dir / "clean.py").write_text("def f(x):\n    return range(x)\n", encoding="utf-8")

        def _clone_per_modern(repo_url, branch="main", depth=1, extra_args=None):
            return str(modern_dir)

        monkeypatch.setattr(
            "app.services.git_sandbox.GitSandboxService.clone_repository", _clone_per_modern
        )
        orchestrator = AutonomousMigrationOrchestrator()
        with pytest.raises(GitOperationError) as exc_info:
            await orchestrator.execute_full_pipeline(
                repo_url=remote,
                github_token="fake-token",
                repo_owner="acme",
                repo_name="legacy",
                base_branch="main",
            )
        message = str(exc_info.value)
        assert "No files could be migrated" in message


class TestWorkerEntrypoint:
    async def test_run_autonomous_job_success(self, local_github, db_session):
        remote = local_github
        user = await make_user(db_session, email="orch@example.com")
        project = Project(owner_id=user.id, name="P", source_language="python")
        db_session.add(project)
        await db_session.flush()
        job = MigrationJob(
            project_id=project.id,
            title="autonomous",
            context_rule=None,
            input_code="# input",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        from app.services.orchestrator import run_autonomous_migration_job

        class FakeRedis:
            def __init__(self):
                self.writes = []

            async def set(self, key, value, **kwargs):
                self.writes.append(key)

        result = await run_autonomous_migration_job(
            {"redis": FakeRedis()},
            job.id,
            remote,
            "acme",
            "legacy",
            encrypt_token("fake-token"),
            None,
            "main",
        )
        await db_session.refresh(job)
        assert job.status == JobStatus.completed.value
        assert job.metrics["pull_request_url"] == "https://github.com/acme/legacy/pull/7"
        assert result["pull_request_url"] == "https://github.com/acme/legacy/pull/7"

    async def test_run_autonomous_job_failure(self, monkeypatch, db_session, legacy_repo):
        _repo_dir, remote = legacy_repo

        def _clone_fails(repo_url, branch="main", depth=1, extra_args=None):
            raise GitOperationError("boom")

        monkeypatch.setattr(
            "app.services.git_sandbox.GitSandboxService.clone_repository", _clone_fails
        )

        user = await make_user(db_session, email="orch2@example.com")
        project = Project(owner_id=user.id, name="P", source_language="python")
        db_session.add(project)
        await db_session.flush()
        job = MigrationJob(
            project_id=project.id, title="autonomous", context_rule=None, input_code="# input"
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        from app.services.orchestrator import run_autonomous_migration_job

        class FakeRedis:
            async def set(self, key, value, **kwargs):
                pass

        with pytest.raises(GitOperationError):
            await run_autonomous_migration_job(
                {"redis": FakeRedis()},
                job.id,
                remote,
                "acme",
                "legacy",
                encrypt_token("token"),
                None,
                "main",
            )
        await db_session.refresh(job)
        assert job.status == JobStatus.failed.value
        assert job.error_message


class TestDirectoryWalkers:
    async def test_process_dir_async(self, monkeypatch, tmp_path):
        (tmp_path / "mod.py").write_text("for i in xrange(3):\n    pass\n", encoding="utf-8")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "skip.py").write_text("x=1\n", encoding="utf-8")

        async def refactor(code, rule):
            return code.replace("xrange", "range")

        changes = await AutonomousMigrationOrchestrator._process_dir_async(
            str(tmp_path), refactor, ""
        )
        assert len(changes) == 1
        assert changes[0].rel_path == "mod.py"

    async def test_process_dir_async_skips_unreadable(self, monkeypatch, tmp_path):
        broken = tmp_path / "broken.py"
        broken.write_bytes(b"\xff\xfe\x00invalid utf8")

        async def refactor(code, rule):
            return "changed"

        changes = await AutonomousMigrationOrchestrator._process_dir_async(
            str(tmp_path), refactor, ""
        )
        assert changes == []

    async def test_process_dir_async_with_target_files(self, tmp_path):
        (tmp_path / "a.py").write_text("for i in xrange(1):\n    pass\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("for i in xrange(2):\n    pass\n", encoding="utf-8")
        (tmp_path / "c.py").write_text("for i in xrange(3):\n    pass\n", encoding="utf-8")

        async def refactor(code, rule):
            return code.replace("xrange", "range")

        changes = await AutonomousMigrationOrchestrator._process_dir_async(
            str(tmp_path), refactor, "", target_files=["a.py", "c.py"]
        )
        paths = [c.rel_path for c in changes]
        assert paths == ["a.py", "c.py"]

    async def test_process_dir_async_target_files_ignores_missing(self, tmp_path):
        (tmp_path / "a.py").write_text("for i in xrange(1):\n    pass\n", encoding="utf-8")

        async def refactor(code, rule):
            return code.replace("xrange", "range")

        changes = await AutonomousMigrationOrchestrator._process_dir_async(
            str(tmp_path), refactor, "", target_files=["a.py", "does-not-exist.py", "b.txt"]
        )
        assert [c.rel_path for c in changes] == ["a.py"]

    async def test_missing_target_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.py").write_text("x=1\n", encoding="utf-8")
        missing = AutonomousMigrationOrchestrator._missing_target_files(
            str(tmp_path),
            ["a.py", "sub/b.py", "src/app.py", "docs/README.md", "not.py"],
        )
        assert missing == ["src/app.py", "docs/README.md", "not.py"]

    async def test_heal_dir_async(self, tmp_path):
        (tmp_path / "mod.py").write_text("for i in xrange(3):\n    pass\n", encoding="utf-8")
        error = f'File "{tmp_path}/mod.py", line 1, in <module>\nNameError: xrange'

        async def heal(code, err, rule):
            return code.replace("xrange", "range")

        changes = await AutonomousMigrationOrchestrator._heal_dir_async(
            str(tmp_path), error, heal, ""
        )
        assert len(changes) == 1
        assert "range(3)" in changes[0].after


class TestNamingHelpers:
    def test_default_title(self):
        assert "acme/legacy" in AutonomousMigrationOrchestrator._default_title("acme", "legacy")

    def test_default_commit_message(self):
        from app.services.git_sandbox import FileChange

        change = FileChange(rel_path="a.py", before="a", after="b")
        msg = AutonomousMigrationOrchestrator._default_commit_message([change])
        assert "(1 files)" in msg

    def test_default_body_lists_files(self):
        from app.services.git_sandbox import FileChange

        change = FileChange(rel_path="a.py", before="a", after="b")
        body = AutonomousMigrationOrchestrator._default_body([change])
        assert "`a.py`" in body
