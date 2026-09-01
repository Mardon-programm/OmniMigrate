"""Live end-to-end API tests against a running OmniMigrate stack.

Opt-in: runs only when OMNI_LIVE_BASE_URL is set, e.g.

    OMNI_LIVE_BASE_URL=http://localhost:8003 pytest tests/integration -m live

Covers the core revenue path: health → auth → project → migration job → diff.
"""

import asyncio
import os
import uuid

import httpx
import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.live,
]

LIVE_URL = os.environ.get("OMNI_LIVE_BASE_URL", "").rstrip("/")

pytestmark_skip = pytest.mark.skipif(
    not LIVE_URL, reason="OMNI_LIVE_BASE_URL not set; skipping live stack tests"
)

LEGACY_SNIPPET = """import datetime
import distutils.core


def stamp():
    return datetime.datetime.utcnow()


def build():
    return distutils.core.Distribution(name="demo")
"""


@pytest.fixture()
async def api():
    assert LIVE_URL, "OMNI_LIVE_BASE_URL required"
    async with httpx.AsyncClient(base_url=LIVE_URL, timeout=30) as c:
        yield c


async def _register(api: httpx.AsyncClient) -> dict:
    email = f"live_{uuid.uuid4().hex[:10]}@example.com"
    resp = await api.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "LiveTest123!", "full_name": "Live Test"},
    )
    resp.raise_for_status()
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(not LIVE_URL, reason="OMNI_LIVE_BASE_URL not set")
async def test_health_and_readiness(api):
    assert (await api.get("/healthz")).status_code == 200
    ready = await api.get("/readyz")
    assert ready.status_code == 200
    body = ready.json()
    assert body.get("database") in ("ok", True)
    assert body.get("redis") in ("ok", True)


@pytest.mark.skipif(not LIVE_URL, reason="OMNI_LIVE_BASE_URL not set")
async def test_full_migration_flow(api):
    tokens = await _register(api)
    headers = _auth(tokens["access_token"])

    me = await api.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"].startswith("live_")

    proj = await api.post(
        "/api/v1/projects",
        json={
            "name": f"live-{uuid.uuid4().hex[:8]}",
            "description": "Live integration",
            "source_language": "python",
            "target_stack": "python3.12",
        },
        headers=headers,
    )
    assert proj.status_code == 201, proj.text
    project_id = proj.json()["id"]

    job = await api.post(
        "/api/v1/jobs",
        json={
            "project_id": project_id,
            "title": "Live smoke migration",
            "input_code": LEGACY_SNIPPET,
            "priority": "urgent",
        },
        headers=headers,
    )
    assert job.status_code == 202, job.text
    job_id = job.json()["id"]

    # Poll until the worker finishes (max ~60s).
    final = None
    for _ in range(30):
        status = await api.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert status.status_code == 200
        data = status.json()
        if data["status"] in ("completed", "failed"):
            final = data
            break
        await asyncio.sleep(2)

    assert final is not None, "job did not finish in time"
    assert final["status"] == "completed", final.get("error_message")
    assert final["output_code"]
    assert "distutils" not in final["output_code"]

    diff = await api.get(f"/api/v1/jobs/{job_id}/diff", headers=headers)
    assert diff.status_code == 200
    assert "+" in diff.json()["diff"]
