import app.core.database as _db
from app.models import JobStatus
from app.services.migration_service import STATE_KEY
from tests.conftest import auth_headers, make_user

VALID_REPO = "https://github.com/acme/legacy.git"


async def _run_payload(**overrides):
    payload = {
        "repo_url": VALID_REPO,
        "repo_owner": "acme",
        "repo_name": "legacy",
        "github_token": "ghp_fake_token",
        "context_rule": None,
        "base_branch": "main",
        "title": None,
        "body": None,
    }
    payload.update(overrides)
    return payload


class TestRunAutonomous:
    async def test_run_enqueues_job(self, client, db_session):
        user = await make_user(db_session, email="auto@example.com")
        resp = await client.post(
            "/api/v1/autonomous/run",
            headers=auth_headers(user.id),
            json=await _run_payload(),
        )
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["job_id"]
        assert body["status"] == JobStatus.queued.value

    async def test_run_rejects_bad_url(self, client, db_session):
        user = await make_user(db_session, email="auto2@example.com")
        resp = await client.post(
            "/api/v1/autonomous/run",
            headers=auth_headers(user.id),
            json=await _run_payload(repo_url="file:///etc/passwd"),
        )
        assert resp.status_code == 422

    async def test_run_rejects_unknown_host(self, client, db_session):
        user = await make_user(db_session, email="auto3@example.com")
        resp = await client.post(
            "/api/v1/autonomous/run",
            headers=auth_headers(user.id),
            json=await _run_payload(repo_url="https://internal.corp/foo/bar.git"),
        )
        assert resp.status_code == 422

    async def test_run_queue_failure_returns_503(self, client, db_session, monkeypatch):
        user = await make_user(db_session, email="auto4@example.com")

        async def _boom(**kwargs):
            raise RuntimeError("queue down")

        monkeypatch.setattr("app.api.v1.autonomous_migration.enqueue_autonomous_migration", _boom)
        resp = await client.post(
            "/api/v1/autonomous/run",
            headers=auth_headers(user.id),
            json=await _run_payload(),
        )
        assert resp.status_code == 503

    async def test_run_uses_existing_project(self, client, db_session):
        user = await make_user(db_session, email="auto5@example.com")
        headers = auth_headers(user.id)
        await client.post("/api/v1/autonomous/run", headers=headers, json=await _run_payload())
        resp = await client.post(
            "/api/v1/autonomous/run", headers=headers, json=await _run_payload()
        )
        assert resp.status_code == 202
        resp.json()
        projects = await client.get("/api/v1/projects", headers=headers)
        assert len(projects.json()) == 1


class TestGetAutonomousJob:
    async def test_get_job_detail(self, client, db_session):
        user = await make_user(db_session, email="auto6@example.com")
        created = (
            await client.post(
                "/api/v1/autonomous/run",
                headers=auth_headers(user.id),
                json=await _run_payload(),
            )
        ).json()
        resp = await client.get(
            f"/api/v1/autonomous/jobs/{created['job_id']}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == created["job_id"]
        assert body["status"] == JobStatus.queued.value

    async def test_get_missing_job(self, client, db_session):
        user = await make_user(db_session, email="auto7@example.com")
        resp = await client.get("/api/v1/autonomous/jobs/9999", headers=auth_headers(user.id))
        assert resp.status_code == 404

    async def test_get_foreign_job(self, client, db_session):
        user = await make_user(db_session, email="auto8@example.com")
        other = await make_user(db_session, email="auto9@example.com")
        created = (
            await client.post(
                "/api/v1/autonomous/run",
                headers=auth_headers(user.id),
                json=await _run_payload(),
            )
        ).json()
        resp = await client.get(
            f"/api/v1/autonomous/jobs/{created['job_id']}",
            headers=auth_headers(other.id),
        )
        assert resp.status_code == 403

    async def test_get_job_with_live_state(self, client, db_session):
        import json

        user = await make_user(db_session, email="auto_live@example.com")
        created = (
            await client.post(
                "/api/v1/autonomous/run",
                headers=auth_headers(user.id),
                json=await _run_payload(),
            )
        ).json()
        job_id = created["job_id"]
        await _db._redis_pool.set(
            STATE_KEY.format(job_id=job_id),
            json.dumps({"status": "refactoring", "progress": 60, "message": "healing"}),
        )
        resp = await client.get(
            f"/api/v1/autonomous/jobs/{job_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "refactoring"
        assert body["progress"] == 60
        assert body["message"] == "healing"

    async def test_get_job_with_invalid_json_in_redis(self, client, db_session):
        user = await make_user(db_session, email="auto_badjson@example.com")
        created = (
            await client.post(
                "/api/v1/autonomous/run",
                headers=auth_headers(user.id),
                json=await _run_payload(),
            )
        ).json()
        job_id = created["job_id"]
        await _db._redis_pool.set(STATE_KEY.format(job_id=job_id), "not-json")
        resp = await client.get(
            f"/api/v1/autonomous/jobs/{job_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == JobStatus.queued.value

    async def test_get_job_requires_auth(self, client, db_session):
        resp = await client.get("/api/v1/autonomous/jobs/9999")
        assert resp.status_code == 401
