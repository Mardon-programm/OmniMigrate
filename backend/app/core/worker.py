from __future__ import annotations

from contextlib import asynccontextmanager
from typing import ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import AsyncSessionLocal


@asynccontextmanager
async def create_session():
    """Async context manager yielding an AsyncSession for worker tasks."""
    async with AsyncSessionLocal() as session:
        yield session


async def _startup(ctx: dict) -> None:
    pass


async def _shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    """Arq configuration used by `arq app.core.worker.WorkerSettings`.

    Listens to all priority queues; arq drains them in the order listed,
    so urgent jobs are picked up before normal/bulk.
    """

    functions: ClassVar[list[str]] = [
        "app.services.migration_service.run_migration_job",
        "app.services.orchestrator.run_autonomous_migration_job",
    ]
    queues: ClassVar[list[str]] = [
        "omnimigrate:urgent",
        "omnimigrate:normal",
        "omnimigrate:bulk",
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = _startup
    on_shutdown = _shutdown
    max_jobs = 4
    job_timeout = 1200
    keep_result = 3600


# Optional periodic cron job placeholder for future scheduled maintenance.
async def healthcheck_cron(ctx: dict) -> None:
    return None


cron_jobs = [cron(healthcheck_cron, minute=10)]
