import httpx
import pytest


class TestAppRoot:
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["app"] == "OmniMigrate"
        assert resp.json()["health"] == "/healthz"

    async def test_healthz(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_openapi(self, client):
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        assert resp.json()["info"]["title"] == "OmniMigrate"


@pytest.fixture()
async def tolerant_client():
    from app.main import app

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestExceptionHandlers:
    async def test_unhandled_exception_hides_detail(self, tolerant_client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "debug", False)
        from app.main import app

        app.get("/__boom")(lambda: (_ for _ in ()).throw(RuntimeError("secret detail")))

        resp = await tolerant_client.get("/__boom")
        assert resp.status_code == 500
        assert "secret detail" not in resp.text
        assert resp.json()["code"] == "INTERNAL_ERROR"

    async def test_unhandled_exception_debug_mode(self, tolerant_client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "debug", True)

        resp = await tolerant_client.get("/__boom")
        assert resp.status_code == 500
        assert "secret detail" in resp.text
