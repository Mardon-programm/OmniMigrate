from tests.conftest import auth_headers, make_user

VALID_CODE = "for i in xrange(3):\n    print(i)\n"
MODERN_CODE = "for i in range(3):\n    print(i)\n"


class TestAnalyze:
    async def test_analyze_valid(self, client, db_session):
        user = await make_user(db_session, email="mig@example.com")
        resp = await client.post(
            "/api/v1/migrations/analyze",
            headers=auth_headers(user.id),
            json={"code": VALID_CODE, "filename": "legacy.py"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["findings"]

    async def test_analyze_requires_code(self, client, db_session):
        user = await make_user(db_session, email="mig2@example.com")
        resp = await client.post(
            "/api/v1/migrations/analyze",
            headers=auth_headers(user.id),
            json={"code": ""},
        )
        assert resp.status_code == 422

    async def test_analyze_too_large(self, client, db_session):
        user = await make_user(db_session, email="mig3@example.com")
        resp = await client.post(
            "/api/v1/migrations/analyze",
            headers=auth_headers(user.id),
            json={"code": "x" * 2_000_001},
        )
        assert resp.status_code == 413


class TestPreviewDiff:
    async def test_preview_diff(self, client, db_session):
        user = await make_user(db_session, email="mig4@example.com")
        resp = await client.post(
            "/api/v1/migrations/preview-diff",
            headers=auth_headers(user.id),
            json={"legacy": VALID_CODE, "modern": MODERN_CODE},
        )
        assert resp.status_code == 200
        assert resp.json()["stats"]["additions"] >= 1

    async def test_preview_diff_requires_auth(self, client):
        resp = await client.post(
            "/api/v1/migrations/preview-diff", json={"legacy": "x", "modern": "y"}
        )
        assert resp.status_code == 401


class TestEngineHealth:
    async def test_health(self, client, db_session):
        user = await make_user(db_session, email="mig5@example.com")
        resp = await client.get("/api/v1/migrations/health", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"
        assert "sandbox-verification" in resp.json()["capabilities"]
