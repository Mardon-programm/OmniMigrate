"""MFA (TOTP) flow tests: setup → enable → login requires code → disable."""

import pyotp
import pytest
from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.asyncio


async def _setup_mfa(client, db_session, email="mfa@example.com"):
    user = await make_user(db_session, email=email)
    headers = auth_headers(user.id, user.role.value)
    resp = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return user, headers, data


async def test_mfa_setup_returns_secret_and_uri(client, db_session):
    _, _, data = await _setup_mfa(client, db_session)
    assert len(data["secret"]) >= 32
    assert data["otpauth_uri"].startswith("otpauth://totp/OmniMigrate:")


async def test_mfa_setup_conflict_when_already_enabled(client, db_session):
    user, headers, data = await _setup_mfa(client, db_session)
    code = pyotp.TOTP(data["secret"]).now()
    resp = await client.post("/api/v1/auth/mfa/enable", json={"code": code}, headers=headers)
    assert resp.status_code == 200, resp.text
    resp = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert resp.status_code == 409


async def test_mfa_enable_rejects_bad_code(client, db_session):
    _, headers, _ = await _setup_mfa(client, db_session)
    resp = await client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=headers)
    assert resp.status_code == 400


async def test_login_requires_mfa_code(client, db_session):
    user, _, data = await _setup_mfa(client, db_session)
    code = pyotp.TOTP(data["secret"]).now()
    resp = await client.post(
        "/api/v1/auth/mfa/enable", json={"code": code}, headers=auth_headers(user.id)
    )
    assert resp.status_code == 200

    # Without code -> 401 + X-MFA-Required header
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@example.com", "password": "password123"},
    )
    assert resp.status_code == 401
    assert resp.headers.get("x-mfa-required") == "true"

    # With wrong code -> 401
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa@example.com",
            "password": "password123",
            "mfa_code": "000000",
        },
    )
    assert resp.status_code == 401

    # With valid code -> tokens issued
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "mfa@example.com",
            "password": "password123",
            "mfa_code": pyotp.TOTP(data["secret"]).now(),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_mfa_disable_requires_password_and_code(client, db_session):
    user, headers, data = await _setup_mfa(client, db_session)
    totp = pyotp.TOTP(data["secret"])
    await client.post(
        "/api/v1/auth/mfa/enable",
        json={"code": totp.now()},
        headers=headers,
    )

    # Wrong password
    resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "wrongpass123", "code": totp.now()},
        headers=headers,
    )
    assert resp.status_code == 403

    # Correct password + code
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.json()["mfa_enabled"] is True
    resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "password123", "code": totp.now()},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["mfa_enabled"] is False

    # Login without MFA works again
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@example.com", "password": "password123"},
    )
    assert resp.status_code == 200


async def test_me_exposes_mfa_flag(client, db_session):
    user = await make_user(db_session, email="flag@example.com")
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(user.id))
    assert resp.status_code == 200
    assert resp.json()["mfa_enabled"] is False
