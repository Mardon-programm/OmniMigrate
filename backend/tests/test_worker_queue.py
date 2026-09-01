class TestWorkerSettings:
    def test_functions_registered(self):
        from app.core.worker import WorkerSettings

        assert "app.services.migration_service.run_migration_job" in WorkerSettings.functions
        assert "app.services.orchestrator.run_autonomous_migration_job" in WorkerSettings.functions

    def test_priority_queues_listed(self):
        from app.core.worker import WorkerSettings

        assert WorkerSettings.queues == [
            "omnimigrate:urgent",
            "omnimigrate:normal",
            "omnimigrate:bulk",
        ]

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


class TestQueueNames:
    def test_queue_name_mapping(self):
        from app.services.queue import DEFAULT_QUEUE, queue_name

        assert queue_name("urgent") == "omnimigrate:urgent"
        assert queue_name("normal") == "omnimigrate:normal"
        assert queue_name("bulk") == "omnimigrate:bulk"
        assert queue_name(None) == "omnimigrate:normal"
        assert queue_name("bogus") == "omnimigrate:normal"
        assert DEFAULT_QUEUE == "omnimigrate:normal"


class TestQueue:
    async def test_enqueue_migration_job_default_priority(self, monkeypatch):
        from app.services import queue as queue_module

        calls = []

        class FakePool:
            async def enqueue_job(self, fn, job_id, **kwargs):
                calls.append((fn, job_id, kwargs))

            async def aclose(self):
                calls.append("closed")

        async def _fake_create_pool(_settings):
            return FakePool()

        monkeypatch.setattr(queue_module, "create_pool", _fake_create_pool)
        await queue_module.enqueue_migration_job(123)
        assert calls == [
            (
                "app.services.migration_service.run_migration_job",
                123,
                {"_queue_name": "omnimigrate:normal"},
            ),
            "closed",
        ]

    async def test_enqueue_migration_job_urgent(self, monkeypatch):
        from app.services import queue as queue_module

        calls = []

        class FakePool:
            async def enqueue_job(self, fn, job_id, **kwargs):
                calls.append((fn, job_id, kwargs))

            async def aclose(self):
                calls.append("closed")

        async def _fake_create_pool(_settings):
            return FakePool()

        monkeypatch.setattr(queue_module, "create_pool", _fake_create_pool)
        await queue_module.enqueue_migration_job(5, priority="urgent")
        assert calls[0][2] == {"_queue_name": "omnimigrate:urgent"}

    async def test_enqueue_autonomous_migration(self, monkeypatch):
        from app.services import queue as queue_module

        calls = []

        class FakePool:
            async def enqueue_job(self, *args, **kwargs):
                calls.append((args, kwargs))

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
            priority="bulk",
        )
        args, kwargs = calls[0]
        assert args[0] == "app.services.orchestrator.run_autonomous_migration_job"
        assert args[1] == 7
        assert kwargs["_queue_name"] == "omnimigrate:bulk"
        assert calls[-1] == "closed"
