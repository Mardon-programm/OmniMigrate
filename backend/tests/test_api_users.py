from app.models import UserRole
from tests.conftest import auth_headers, make_user


class TestUsers:
    async def test_list_users_requires_admin(self, client, db_session):
        user = await make_user(db_session, email="u1@example.com")
        resp = await client.get("/api/v1/users", headers=auth_headers(user.id))
        assert resp.status_code == 403

    async def test_list_users_as_admin(self, client, db_session):
        admin = await make_user(db_session, email="admin@example.com", role=UserRole.admin)
        await make_user(db_session, email="u2@example.com")
        resp = await client.get(
            "/api/v1/users", headers=auth_headers(admin.id, UserRole.admin.value)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_get_self(self, client, db_session):
        user = await make_user(db_session, email="u3@example.com")
        resp = await client.get(f"/api/v1/users/{user.id}", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json()["email"] == "u3@example.com"

    async def test_get_other_forbidden(self, client, db_session):
        a = await make_user(db_session, email="u4@example.com")
        b = await make_user(db_session, email="u5@example.com")
        resp = await client.get(f"/api/v1/users/{b.id}", headers=auth_headers(a.id))
        assert resp.status_code == 403

    async def test_get_missing(self, client, db_session):
        user = await make_user(db_session, email="u6@example.com")
        resp = await client.get("/api/v1/users/9999", headers=auth_headers(user.id))
        assert resp.status_code == 404

    async def test_create_user_requires_admin(self, client, db_session):
        user = await make_user(db_session, email="u7@example.com")
        resp = await client.post(
            "/api/v1/users",
            headers=auth_headers(user.id),
            json={
                "email": "new@example.com",
                "password": "password123",
                "full_name": "New",
            },
        )
        assert resp.status_code == 403

    async def test_create_user_as_admin(self, client, db_session):
        admin = await make_user(db_session, email="admin2@example.com", role=UserRole.admin)
        resp = await client.post(
            "/api/v1/users",
            headers=auth_headers(admin.id, UserRole.admin.value),
            json={
                "email": "new2@example.com",
                "password": "password123",
                "full_name": "New",
                "role": "engineer",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "engineer"

    async def test_create_user_duplicate(self, client, db_session):
        admin = await make_user(db_session, email="admin3@example.com", role=UserRole.admin)
        await make_user(db_session, email="dup@example.com")
        resp = await client.post(
            "/api/v1/users",
            headers=auth_headers(admin.id, UserRole.admin.value),
            json={
                "email": "dup@example.com",
                "password": "password123",
                "full_name": "Dup",
            },
        )
        assert resp.status_code == 409

    async def test_update_self_name(self, client, db_session):
        user = await make_user(db_session, email="u8@example.com")
        resp = await client.patch(
            f"/api/v1/users/{user.id}",
            headers=auth_headers(user.id),
            json={"full_name": "Renamed"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Renamed"

    async def test_update_own_role_forbidden(self, client, db_session):
        user = await make_user(db_session, email="u9@example.com")
        resp = await client.patch(
            f"/api/v1/users/{user.id}",
            headers=auth_headers(user.id),
            json={"role": "admin"},
        )
        assert resp.status_code == 403

    async def test_update_other_forbidden(self, client, db_session):
        a = await make_user(db_session, email="u10@example.com")
        b = await make_user(db_session, email="u11@example.com")
        resp = await client.patch(
            f"/api/v1/users/{b.id}",
            headers=auth_headers(a.id),
            json={"full_name": "Hacked"},
        )
        assert resp.status_code == 403

    async def test_change_own_password(self, client, db_session):
        user = await make_user(db_session, email="pw@example.com")
        resp = await client.post(
            f"/api/v1/users/{user.id}/password",
            headers=auth_headers(user.id),
            json={"current_password": "password123", "new_password": "newpassword123"},
        )
        assert resp.status_code == 204

    async def test_change_password_wrong_current(self, client, db_session):
        user = await make_user(db_session, email="pw2@example.com")
        resp = await client.post(
            f"/api/v1/users/{user.id}/password",
            headers=auth_headers(user.id),
            json={"current_password": "wrong-password", "new_password": "newpassword123"},
        )
        assert resp.status_code == 400

    async def test_change_other_password_forbidden(self, client, db_session):
        a = await make_user(db_session, email="pw3@example.com")
        b = await make_user(db_session, email="pw4@example.com")
        resp = await client.post(
            f"/api/v1/users/{b.id}/password",
            headers=auth_headers(a.id),
            json={"current_password": "password123", "new_password": "newpassword123"},
        )
        assert resp.status_code == 403
