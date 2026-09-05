import asyncio
import os
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment MUST be configured before any app module import.
# ---------------------------------------------------------------------------
_TEST_DB = Path(tempfile.gettempdir()) / "omnimigrate_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["REDIS_URL"] = "redis://localhost:1"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_BASE_URL"] = ""
os.environ["LLM_FALLBACK_TO_RULES"] = "true"
os.environ["WORKSPACE_ROOT"] = str(Path(tempfile.gettempdir()) / "omnimigrate_test_ws")
os.environ["SANDBOX_ENABLED"] = "false"
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

import httpx  # noqa: E402
import pytest  # noqa: E402
import sqlalchemy.ext.asyncio as _sa_ext  # noqa: E402
from sqlalchemy import event, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

# Patch create_async_engine so the production code's pool_size / max_overflow
# kwargs don't blow up on SQLite / NullPool.
_orig_caete = _sa_ext.create_async_engine


def _sqlite_safe_engine(url, **kw):
    if "sqlite" in str(url):
        for k in ("pool_size", "max_overflow", "pool_pre_ping", "pool_recycle"):
            kw.pop(k, None)
    return _orig_caete(url, **kw)


_sa_ext.create_async_engine = _sqlite_safe_engine  # type: ignore[assignment]

import app.core.database as database  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402


# ---------------------------------------------------------------------------
# FakeRedis — in-memory dict that satisfies the redis.asyncio interface used
# by rate_limit, jobs, and autonomous_migration routes.
# ---------------------------------------------------------------------------
class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, **_kw: object) -> bool:
        self._store[key] = str(value)
        return True

    async def setex(self, key: str, _time: int, value: str) -> bool:
        self._store[key] = str(value)
        return True

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, "0")) + 1
        self._store[key] = str(val)
        return val

    async def flushdb(self) -> None:
        self._store.clear()

    async def aclose(self) -> None:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# SQLite engine (replaces the Postgres engine created at import time).
# ---------------------------------------------------------------------------
# Override the module-level engine / session factory with proper SQLite args.
# ---------------------------------------------------------------------------
test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_TEST_DB}",
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)
database.engine = test_engine
database.AsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _rec):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Fake Redis pool — used by get_redis() in API routes.
# ---------------------------------------------------------------------------
_fake_redis = FakeRedis()
database._redis_pool = _fake_redis


# ---------------------------------------------------------------------------
# Patch queue enqueue functions to no-ops so tests don't need a real Redis
# for arq.  Individual tests can still monkeypatch these to simulate errors.
# ---------------------------------------------------------------------------
import app.api.v1.autonomous_migration as _auto_mod  # noqa: E402
import app.api.v1.jobs as _jobs_mod  # noqa: E402
import app.services.queue as _queue_mod  # noqa: E402

# Capture originals from the source module BEFORE any patching.
_real_enqueue_migration = _queue_mod.enqueue_migration_job
_real_enqueue_autonomous = _queue_mod.enqueue_autonomous_migration


async def _noop_enqueue_migration(job_id: int, priority: str | None = None) -> None:
    pass


async def _noop_enqueue_autonomous(
    job_id: int,
    repo_url: str = "",
    repo_owner: str = "",
    repo_name: str = "",
    github_token: str = "",
    context_rule: str | None = None,
    base_branch: str = "main",
    title: str | None = None,
    body: str | None = None,
    priority: str | None = None,
    target_files: list[str] | None = None,
) -> None:
    pass


# Patch only the route modules where the functions are actually called.
_jobs_mod.enqueue_migration_job = _noop_enqueue_migration
_auto_mod.enqueue_autonomous_migration = _noop_enqueue_autonomous

# Verify the patch took effect on route modules.
assert _auto_mod.enqueue_autonomous_migration is _noop_enqueue_autonomous, "auto patch failed"
assert _jobs_mod.enqueue_migration_job is _noop_enqueue_migration, "jobs patch failed"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    async def _create():
        from app.core.database import Base

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    yield

    async def _drop():
        from app.core.database import Base

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_drop())


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    asyncio.run(_clean())


async def _clean():
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM usage_records"))
        await conn.execute(text("DELETE FROM subscriptions"))
        await conn.execute(text("DELETE FROM plans"))
        await conn.execute(text("DELETE FROM password_reset_tokens"))
        await conn.execute(text("DELETE FROM audit_logs"))
        await conn.execute(text("DELETE FROM organization_members"))
        await conn.execute(text("DELETE FROM organizations"))
        await conn.execute(text("DELETE FROM migration_jobs"))
        await conn.execute(text("DELETE FROM projects"))
        await conn.execute(text("DELETE FROM users"))
    _fake_redis._store.clear()


@pytest.fixture()
async def db_session():
    async with database.AsyncSessionLocal() as session:
        yield session


async def make_user(
    session,
    email: str = "tester@example.com",
    password: str = "password123",
    full_name: str = "Test User",
    role: UserRole = UserRole.client,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_headers(user_id: int, role: str = "client") -> dict[str, str]:
    token = create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_user(
    client,
    email: str = "tester@example.com",
    password: str = "password123",
    full_name: str = "Test User",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
