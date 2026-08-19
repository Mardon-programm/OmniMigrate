import app.core.database as _db
from app.models import JobStatus, UserRole
from tests.conftest import auth_headers, make_user


async def _setup_owner_project(client, db_session, email="jowner@example.com"):
    user = await make_user(db_session, email=email)
    headers = auth_headers(user.id)
    resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Job Project", "source_language": "python"},
    )
    assert resp.status_code == 201, resp.text
    return user, headers, resp.json()


async def _submit_job(client, headers, project_id, code='print("hi")\n'):
    return await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "project_id": project_id,
            "title": "Migration job",
            "context_rule": None,
            "input_code": code,
        },
    )


class TestSubmitJob:
    async def test_submit_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        resp = await _submit_job(client, headers, project["id"])
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["status"] == JobStatus.queued.value
        assert body["project_id"] == project["id"]

    async def test_submit_missing_project(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await _submit_job(client, headers, 9999)
        assert resp.status_code == 404

    async def test_submit_foreign_project(self, client, db_session):
        owner = await make_user(db_session, email="fowner@example.com")
        other = await make_user(db_session, email="fother@example.com")
        resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers(owner.id),
            json={"name": "Foreign"},
        )
        project = resp.json()
        resp = await _submit_job(client, auth_headers(other.id), project["id"])
        assert resp.status_code == 403

    async def test_submit_marks_failed_when_queue_down(self, client, db_session, monkeypatch):
        _, headers, project = await _setup_owner_project(client, db_session)

        async def _boom(job_id: int):
            raise RuntimeError("queue down")

        monkeypatch.setattr("app.api.v1.jobs.enqueue_migration_job", _boom)
        resp = await _submit_job(client, headers, project["id"])
        assert resp.status_code == 202
        assert resp.json()["status"] == JobStatus.failed.value


class TestListJobs:
    async def test_list_empty(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await client.get("/api/v1/jobs", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_own_jobs(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        await _submit_job(client, headers, project["id"])
        resp = await client.get("/api/v1/jobs", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_list_filtered_by_project(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        await _submit_job(client, headers, project["id"])
        resp = await client.get(f"/api/v1/jobs?project_id={project['id']}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_list_filter_foreign_project(self, client, db_session):
        owner = await make_user(db_session, email="ljowner@example.com")
        other = await make_user(db_session, email="ljother@example.com")
        resp = await client.post(
            "/api/v1/projects", headers=auth_headers(owner.id), json={"name": "P"}
        )
        project = resp.json()
        resp = await client.get(
            f"/api/v1/jobs?project_id={project['id']}", headers=auth_headers(other.id)
        )
        assert resp.status_code == 403

    async def test_list_as_admin_sees_all(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        await _submit_job(client, headers, project["id"])
        admin = await make_user(db_session, email="ljadmin@example.com", role=UserRole.admin)
        resp = await client.get(
            "/api/v1/jobs", headers=auth_headers(admin.id, UserRole.admin.value)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestGetJob:
    async def test_get_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        resp = await client.get(f"/api/v1/jobs/{job['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == job["id"]

    async def test_get_missing_job(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await client.get("/api/v1/jobs/9999", headers=headers)
        assert resp.status_code == 404

    async def test_get_foreign_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        other = await make_user(db_session, email="gother@example.com")
        resp = await client.get(f"/api/v1/jobs/{job['id']}", headers=auth_headers(other.id))
        assert resp.status_code == 403

    async def test_get_job_status(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        resp = await client.get(f"/api/v1/jobs/{job['id']}/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == job["id"]

    async def test_get_job_diff_when_empty(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        resp = await client.get(f"/api/v1/jobs/{job['id']}/diff", headers=headers)
        assert resp.status_code == 404

    async def test_get_job_output_when_empty(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        resp = await client.get(f"/api/v1/jobs/{job['id']}/output", headers=headers)
        assert resp.status_code == 404


class TestCancelJob:
    async def test_cancel_queued_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        resp = await client.delete(f"/api/v1/jobs/{job['id']}", headers=headers)
        assert resp.status_code == 204

    async def test_cancel_finished_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        from app.services.repositories import JobRepository

        repo = JobRepository(db_session)
        row = await repo.get_by_id(job["id"])
        row.status = JobStatus.completed.value
        await db_session.commit()
        resp = await client.delete(f"/api/v1/jobs/{job['id']}", headers=headers)
        assert resp.status_code == 400

    async def test_cancel_with_live_state(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        from app.api.v1.jobs import STATE_KEY

        state = '{"status":"queued","progress":10}'
        await _db._redis_pool.set(STATE_KEY.format(job_id=job["id"]), state)
        resp = await client.delete(f"/api/v1/jobs/{job['id']}", headers=headers)
        assert resp.status_code == 204

    async def test_cancel_missing_job(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await client.delete("/api/v1/jobs/9999", headers=headers)
        assert resp.status_code == 404

    async def test_cancel_foreign_job(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        other = await make_user(db_session, email="cancel_other@example.com")
        resp = await client.delete(f"/api/v1/jobs/{job['id']}", headers=auth_headers(other.id))
        assert resp.status_code == 403


class TestJobDiffAndOutput:
    async def test_get_diff_with_data(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        from app.services.repositories import JobRepository

        repo = JobRepository(db_session)
        row = await repo.get_by_id(job["id"])
        row.diff = "--- a/old.py\n+++ b/new.py\n@@ -1 +1 @@\n-old\n+new"
        await db_session.commit()
        resp = await client.get(f"/api/v1/jobs/{job['id']}/diff", headers=headers)
        assert resp.status_code == 200
        assert "diff" in resp.json()

    async def test_get_output_with_data(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        from app.services.repositories import JobRepository

        repo = JobRepository(db_session)
        row = await repo.get_by_id(job["id"])
        row.output_code = "print('modernized')"
        await db_session.commit()
        resp = await client.get(f"/api/v1/jobs/{job['id']}/output", headers=headers)
        assert resp.status_code == 200
        assert "output_code" in resp.json()

    async def test_list_filter_missing_project(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await client.get("/api/v1/jobs?project_id=9999", headers=headers)
        assert resp.status_code == 403

    async def test_get_status_with_live_state(self, client, db_session):
        _, headers, project = await _setup_owner_project(client, db_session)
        job = (await _submit_job(client, headers, project["id"])).json()
        from app.api.v1.jobs import STATE_KEY

        await _db._redis_pool.set(
            STATE_KEY.format(job_id=job["id"]),
            '{"status":"running","progress":50,"message":"refactoring..."}',
        )
        resp = await client.get(f"/api/v1/jobs/{job['id']}/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    async def test_list_filter_nonexistent_project(self, client, db_session):
        _, headers, _ = await _setup_owner_project(client, db_session)
        resp = await client.get("/api/v1/jobs?project_id=9999", headers=headers)
        assert resp.status_code == 403
