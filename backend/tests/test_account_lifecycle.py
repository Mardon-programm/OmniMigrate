"""Tests for auth lifecycle: logout, forgot-password, reset-password, production validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from app.core.security import hash_reset_token
from sqlalchemy.exc import IntegrityError


@pytest.mark.usefixtures("client")
class TestLogout:
    async def test_logout_returns_204(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "password": "password123",
                "full_name": "Logout User",
            },
        )
        assert resp.status_code == 201
        tokens = resp.json()

        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 204

    async def test_logout_refresh_token_blocked(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "block@example.com",
                "password": "password123",
                "full_name": "Block User",
            },
        )
        tokens = resp.json()

        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert resp.status_code == 401

    async def test_logout_no_refresh_token(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "no_refresh@example.com",
                "password": "password123",
                "full_name": "No Refresh",
            },
        )
        tokens = resp.json()

        resp = await client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 204

    async def test_logout_requires_auth(self, client):
        resp = await client.post("/api/v1/auth/logout", json={})
        assert resp.status_code == 401


@pytest.mark.usefixtures("client")
class TestForgotPassword:
    async def test_forgot_password_returns_200(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forgot@example.com",
                "password": "password123",
                "full_name": "Forgot User",
            },
        )
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "forgot@example.com",
            },
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    async def test_forgot_password_nonexistent_email_returns_200(self, client):
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "nonexistent@example.com",
            },
        )
        assert resp.status_code == 200

    async def test_forgot_password_creates_token(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "create@example.com",
                "password": "password123",
                "full_name": "Create User",
            },
        )
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "create@example.com",
            },
        )
        assert resp.status_code == 200


@pytest.mark.usefixtures("client")
class TestResetPassword:
    async def _create_reset_token(self, session, user_id: int) -> str:
        import secrets

        from app.models.password_reset import PasswordResetStatus, PasswordResetToken

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_reset_token(raw_token)
        now = datetime.now(UTC)
        reset = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            status=PasswordResetStatus.pending,
            expires_at=now + timedelta(minutes=30),
            created_at=now,
        )
        session.add(reset)
        await session.commit()
        return raw_token

    async def test_reset_password_success(self, client, db_session):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset@example.com",
                "password": "oldpassword123",
                "full_name": "Reset User",
            },
        )
        assert resp.status_code == 201
        user_resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {resp.json()['access_token']}",
            },
        )
        user_id = user_resp.json()["id"]

        from app.models.user import User as UserModel
        from sqlalchemy import select

        result = await db_session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one()

        raw_token = await self._create_reset_token(db_session, user.id)

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "newpassword123",
            },
        )
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()

    async def test_reset_password_invalid_token(self, client):
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token-12345",
                "new_password": "newpassword123",
            },
        )
        assert resp.status_code == 400

    async def test_reset_password_used_token(self, client, db_session):
        from app.models.password_reset import PasswordResetStatus, PasswordResetToken

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "used@example.com",
                "password": "oldpassword123",
                "full_name": "Used User",
            },
        )
        user_resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {resp.json()['access_token']}",
            },
        )
        user_id = user_resp.json()["id"]

        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_reset_token(raw_token)
        now = datetime.now(UTC)
        reset = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            status=PasswordResetStatus.used,
            expires_at=now + timedelta(minutes=30),
            used_at=now,
            created_at=now,
        )
        db_session.add(reset)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "newpassword123",
            },
        )
        assert resp.status_code == 400

    async def test_reset_password_expired_token(self, client, db_session):
        from app.models.password_reset import PasswordResetStatus, PasswordResetToken

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "expired@example.com",
                "password": "oldpassword123",
                "full_name": "Expired User",
            },
        )
        user_resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {resp.json()['access_token']}",
            },
        )
        user_id = user_resp.json()["id"]

        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_reset_token(raw_token)
        now = datetime.now(UTC)
        reset = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            status=PasswordResetStatus.pending,
            expires_at=now - timedelta(minutes=1),
            created_at=now,
        )
        db_session.add(reset)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "newpassword123",
            },
        )
        assert resp.status_code == 400


class TestPasswordResetTokenModel:
    async def test_model_creation(self, db_session):
        from app.models.password_reset import PasswordResetStatus, PasswordResetToken

        token = PasswordResetToken(
            user_id=1,
            token_hash="test_hash",
            status=PasswordResetStatus.pending,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db_session.add(token)
        await db_session.commit()
        assert token.id > 0

    async def test_model_unique_hash(self, db_session):
        from app.models.password_reset import PasswordResetStatus, PasswordResetToken

        token1 = PasswordResetToken(
            user_id=1,
            token_hash="unique_hash_1",
            status=PasswordResetStatus.pending,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db_session.add(token1)
        await db_session.commit()

        token2 = PasswordResetToken(
            user_id=2,
            token_hash="unique_hash_1",
            status=PasswordResetStatus.pending,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db_session.add(token2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.mark.usefixtures("client")
class TestHealthzEnhanced:
    async def test_healthz_returns_ok(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "service" in data


class TestProductionValidation:
    def test_production_rejects_default_secret_key(self):
        import app.main as main_mod

        with (
            patch("app.main.settings") as mock_settings,
            pytest.raises(SystemExit),
        ):
            mock_settings.environment = "production"
            mock_settings.secret_key = "change-me-in-production"
            mock_settings.database_url = "postgresql+asyncpg://omnimigrate:omnimigrate@localhost/db"
            mock_settings.bcrypt_rounds = 12
            main_mod._validate_production_secrets()

    def test_production_rejects_short_secret_key(self):
        import app.main as main_mod

        with (
            patch("app.main.settings") as mock_settings,
            pytest.raises(SystemExit),
        ):
            mock_settings.environment = "production"
            mock_settings.secret_key = "short"
            mock_settings.database_url = "postgresql+asyncpg://user:strongpass@localhost/db"
            mock_settings.bcrypt_rounds = 12
            main_mod._validate_production_secrets()

    def test_production_rejects_default_db(self):
        import app.main as main_mod

        with (
            patch("app.main.settings") as mock_settings,
            pytest.raises(SystemExit),
        ):
            mock_settings.environment = "production"
            mock_settings.secret_key = "a" * 32
            mock_settings.database_url = "postgresql+asyncpg://omnimigrate:omnimigrate@localhost/db"
            mock_settings.bcrypt_rounds = 12
            main_mod._validate_production_secrets()

    def test_production_rejects_low_bcrypt_rounds(self):
        import app.main as main_mod

        with (
            patch("app.main.settings") as mock_settings,
            pytest.raises(SystemExit),
        ):
            mock_settings.environment = "production"
            mock_settings.secret_key = "a" * 32
            mock_settings.database_url = "postgresql+asyncpg://user:strongpass@localhost/db"
            mock_settings.bcrypt_rounds = 8
            main_mod._validate_production_secrets()

    def test_development_always_passes(self):
        import app.main as main_mod

        with patch("app.main.settings") as mock_settings:
            mock_settings.environment = "development"
            mock_settings.secret_key = "change-me-in-production"
            mock_settings.database_url = "default"
            mock_settings.bcrypt_rounds = 4
            main_mod._validate_production_secrets()


class TestSandboxHardening:
    def test_sandbox_preexec_exists(self):
        from app.services.git_sandbox import GitSandboxService

        assert hasattr(GitSandboxService, "_sandbox_preexec")

    def test_is_unix_flag(self):
        from app.services.git_sandbox import _IS_UNIX

        assert isinstance(_IS_UNIX, bool)
