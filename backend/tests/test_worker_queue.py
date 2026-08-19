class TestWorkerSettings:
    def test_functions_registered(self):
        from app.core.worker import WorkerSettings

        assert "app.services.migration_service.run_migration_job" in WorkerSettings.functions
        assert "app.services.orchestrator.run_autonomous_migration_job" in WorkerSettings.functions

    def test_cron_jobs_defined(self):
        from app.core.worker import cron_jobs

        assert len(cron_jobs) >= 1

    async def test_healthcheck_cron_returns_none(self):
        from app.core.worker import healthcheck_cron

        assert await healthcheck_cron({}) is None

    async def test_create_session_yields_session(self):
        from app.core.worker import create_session

        async with create_session() as session:
            assert session is not None


class TestQueue:
    async def test_enqueue_migration_job(self, monkeypatch):
        from app.services import queue as queue_module

        calls = []

        class FakePool:
            async def enqueue_job(self, fn, job_id):
                calls.append((fn, job_id))

            async def aclose(self):
                calls.append("closed")

        async def _fake_create_pool(_settings):
            return FakePool()

        monkeypatch.setattr(queue_module, "create_pool", _fake_create_pool)
        await queue_module.enqueue_migration_job(123)
        assert calls == [
            ("app.services.migration_service.run_migration_job", 123),
            "closed",
        ]

    async def test_enqueue_autonomous_migration(self, monkeypatch):
        from app.services import queue as queue_module

        calls = []

        class FakePool:
            async def enqueue_job(self, *args):
                calls.append(args)

            async def aclose(self):
                calls.append("closed")

        async def _fake_create_pool(_settings):
            return FakePool()

        monkeypatch.setattr(queue_module, "create_pool", _fake_create_pool)
        await queue_module.enqueue_autonomous_migration(
            job_id=7,
            repo_url="https://github.com/acme/legacy.git",
            repo_owner="acme",
            repo_name="legacy",
            github_token="token",
            context_rule=None,
            base_branch="main",
        )
        assert calls[0][0] == "app.services.orchestrator.run_autonomous_migration_job"
        assert calls[0][1] == 7
        assert calls[-1] == "closed"
