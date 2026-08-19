from app.core.config import settings
from app.models import JobStatus, MigrationJob, Project
from app.services.migration_service import MigrationEngine, run_migration_job
from app.services.sandbox import VerificationResult
from tests.conftest import make_user


class FakeRedis:
    def __init__(self, fail_on_set=False):
        self.writes = []
        self.fail_on_set = fail_on_set

    async def set(self, key, value, **kwargs):
        if self.fail_on_set:
            raise RuntimeError("redis down")
        self.writes.append((key, value, kwargs))

    async def get(self, key):
        return None


class FakeSandbox:
    def __init__(self, *results):
        self._results = list(results)

    def verify(self, code):
        return self._results.pop(0)


def _ok(**kwargs):
    defaults = {
        "success": True,
        "syntax_ok": True,
        "runtime_ok": True,
        "errors": [],
        "stdout": "ok",
    }
    defaults.update(kwargs)
    return VerificationResult(**defaults)


def _fail(**kwargs):
    defaults = {
        "success": False,
        "syntax_ok": False,
        "runtime_ok": False,
        "errors": ["SyntaxError: bad"],
        "stdout": "",
    }
    defaults.update(kwargs)
    return VerificationResult(**defaults)


async def _make_job(
    db_session,
    code="for i in xrange(3):\n    print(i)\n",
    status=JobStatus.queued.value,
):
    user = await make_user(db_session, email="migsvc@example.com")
    project = Project(
        owner_id=user.id,
        name="Svc",
        source_language="python",
        target_stack="python-3.12",
    )
    db_session.add(project)
    await db_session.flush()
    job = MigrationJob(
        project_id=project.id,
        title="job",
        context_rule=None,
        input_code=code,
        status=status,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestRunHappyPath:
    async def test_completes_with_local_rules(self, db_session):
        job = await _make_job(db_session)
        engine = MigrationEngine(
            session=db_session,
            redis=FakeRedis(),
            sandbox=FakeSandbox(_ok()),
        )
        await engine.run(job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.completed.value
        assert job.output_code
        assert job.diff
        assert job.completed_at is not None
        assert job.metrics["provider"] == "local-rule-engine"

    async def test_missing_job_returns_silently(self, db_session):
        engine = MigrationEngine(session=db_session, redis=FakeRedis())
        await engine.run(999999)

    async def test_cancelled_job_skips(self, db_session):
        job = await _make_job(db_session, status=JobStatus.cancelled.value)
        engine = MigrationEngine(session=db_session, redis=FakeRedis())
        await engine.run(job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.cancelled.value

    async def test_redis_failure_is_suppressed(self, db_session):
        job = await _make_job(db_session)
        engine = MigrationEngine(
            session=db_session,
            redis=FakeRedis(fail_on_set=True),
            sandbox=FakeSandbox(_ok()),
        )
        await engine.run(job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.completed.value

    async def test_uses_llm_provider(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "openai_api_key", "sk-test")
        job = await _make_job(db_session)
        calls = {"refactor": 0, "heal": 0}

        class FakeLLM:
            async def refactor(self, code, rule, findings):
                calls["refactor"] += 1
                return "def f():\n    return range(3)\n"

            async def self_heal(self, code, error, rule):
                calls["heal"] += 1
                return code

        engine = MigrationEngine(
            session=db_session,
            redis=FakeRedis(),
            llm=FakeLLM(),
            sandbox=FakeSandbox(_ok()),
        )
        await engine.run(job.id)
        await db_session.refresh(job)
        assert calls["refactor"] == 1
        assert job.metrics["provider"] == "llm"
        assert job.status == JobStatus.completed.value


class TestHealLoop:
    async def test_heals_then_completes(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "max_self_heal_attempts", 3)
        job = await _make_job(db_session)
        engine = MigrationEngine(
            session=db_session,
            redis=FakeRedis(),
            sandbox=FakeSandbox(_fail(), _ok()),
        )
        await engine.run(job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.completed.value
        assert job.self_heal_attempts == 1

    async def test_fails_after_exhausting_attempts(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "max_self_heal_attempts", 2)
        job = await _make_job(db_session)
        engine = MigrationEngine(
            session=db_session,
            redis=FakeRedis(),
            sandbox=FakeSandbox(_fail(), _fail(), _fail()),
        )
        await engine.run(job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.failed.value
        assert job.error_message
        assert job.self_heal_attempts == 2


class TestEncodeState:
    def test_encode_state_roundtrip(self):
        import json

        raw = MigrationEngine._encode_state("running", 42, "hello")
        data = json.loads(raw)
        assert data["status"] == "running"
        assert data["progress"] == 42
        assert data["message"] == "hello"
        assert "timestamp" in data


class TestWorkerEntrypoint:
    async def test_run_migration_job(self, db_session):
        job = await _make_job(db_session)
        await run_migration_job({"redis": FakeRedis()}, job.id)
        await db_session.refresh(job)
        assert job.status == JobStatus.completed.value
