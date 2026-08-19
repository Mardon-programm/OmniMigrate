from tests.conftest import auth_headers, make_user, register_user


class TestRegister:
    async def test_register_success(self, client):
        data = await register_user(client)
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"

    async def test_register_rejects_privileged_role(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "password123",
                "full_name": "Admin",
                "role": "admin",
            },
        )
        assert resp.status_code == 403

    async def test_register_duplicate_email(self, client, db_session):
        await make_user(db_session, email="dup@example.com")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "password": "password123",
                "full_name": "Dup",
            },
        )
        assert resp.status_code == 409

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123", "full_name": "X"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client, db_session):
        await make_user(db_session, email="login@example.com")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_login_wrong_password(self, client, db_session):
        await make_user(db_session, email="wrong@example.com")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect-pass"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert resp.status_code == 401

    async def test_login_disabled_account(self, client, db_session):
        await make_user(db_session, email="disabled@example.com", is_active=False)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@example.com", "password": "password123"},
        )
        assert resp.status_code == 403


class TestRefresh:
    async def test_refresh_roundtrip(self, client):
        data = await register_user(client)
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_refresh_with_access_token_rejected(self, client):
        data = await register_user(client)
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["access_token"]}
        )
        assert resp.status_code == 401

    async def test_refresh_garbage_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
        assert resp.status_code == 401


class TestMe:
    async def test_me(self, client, db_session):
        user = await make_user(db_session, email="me@example.com")
        headers = auth_headers(user.id, user.role.value)
        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    async def test_me_requires_token(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_rejects_bad_token(self, client):
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401

    async def test_refresh_deactivated_user(self, client, db_session):
        from app.core.security import create_refresh_token

        user = await make_user(db_session, email="deact@example.com")
        token = create_refresh_token(user.id)
        user.is_active = False
        await db_session.commit()
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 401
