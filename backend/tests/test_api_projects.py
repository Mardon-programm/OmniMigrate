from app.models import UserRole
from tests.conftest import auth_headers, make_user


async def _create_project(client, headers, name="My Project"):
    resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": name,
            "description": "desc",
            "repo_url": "https://github.com/acme/legacy",
            "source_language": "python",
            "target_stack": "python-3.12",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestProjects:
    async def test_list_empty(self, client, db_session):
        user = await make_user(db_session, email="owner@example.com")
        resp = await client.get("/api/v1/projects", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_and_list(self, client, db_session):
        user = await make_user(db_session, email="owner2@example.com")
        headers = auth_headers(user.id)
        created = await _create_project(client, headers)
        assert created["name"] == "My Project"
        assert created["owner_id"] == user.id
        assert created["job_count"] == 0

        resp = await client.get("/api/v1/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_project(self, client, db_session):
        user = await make_user(db_session, email="owner3@example.com")
        headers = auth_headers(user.id)
        created = await _create_project(client, headers)
        resp = await client.get(f"/api/v1/projects/{created['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_foreign_project_forbidden(self, client, db_session):
        owner = await make_user(db_session, email="owner4@example.com")
        other = await make_user(db_session, email="other@example.com")
        created = await _create_project(client, auth_headers(owner.id))
        resp = await client.get(f"/api/v1/projects/{created['id']}", headers=auth_headers(other.id))
        assert resp.status_code == 403

    async def test_get_missing_project(self, client, db_session):
        user = await make_user(db_session, email="owner5@example.com")
        resp = await client.get("/api/v1/projects/9999", headers=auth_headers(user.id))
        assert resp.status_code == 404

    async def test_update_project(self, client, db_session):
        user = await make_user(db_session, email="owner6@example.com")
        headers = auth_headers(user.id)
        created = await _create_project(client, headers)
        resp = await client.patch(
            f"/api/v1/projects/{created['id']}",
            headers=headers,
            json={"name": "Renamed", "description": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    async def test_update_missing_project(self, client, db_session):
        user = await make_user(db_session, email="owner7@example.com")
        resp = await client.patch(
            "/api/v1/projects/9999",
            headers=auth_headers(user.id),
            json={"name": "X"},
        )
        assert resp.status_code == 404

    async def test_delete_requires_admin(self, client, db_session):
        owner = await make_user(db_session, email="owner8@example.com")
        created = await _create_project(client, auth_headers(owner.id))
        resp = await client.delete(
            f"/api/v1/projects/{created['id']}", headers=auth_headers(owner.id)
        )
        assert resp.status_code == 403

    async def test_delete_as_admin(self, client, db_session):
        owner = await make_user(db_session, email="owner9@example.com")
        admin = await make_user(db_session, email="admin9@example.com", role=UserRole.admin)
        created = await _create_project(client, auth_headers(owner.id))
        resp = await client.delete(
            f"/api/v1/projects/{created['id']}",
            headers=auth_headers(admin.id, UserRole.admin.value),
        )
        assert resp.status_code == 204

    async def test_delete_missing_project(self, client, db_session):
        admin = await make_user(db_session, email="admin10@example.com", role=UserRole.admin)
        resp = await client.delete(
            "/api/v1/projects/9999",
            headers=auth_headers(admin.id, UserRole.admin.value),
        )
        assert resp.status_code == 404
