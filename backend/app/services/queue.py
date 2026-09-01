from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings
from app.models.migration_job import JobPriority

# Dedicated queue per priority; workers listen to all three, urgent drains first.
QUEUE_NAMES: dict[str, str] = {
    JobPriority.urgent.value: "omnimigrate:urgent",
    JobPriority.normal.value: "omnimigrate:normal",
    JobPriority.bulk.value: "omnimigrate:bulk",
}
DEFAULT_QUEUE = QUEUE_NAMES[JobPriority.normal.value]


def queue_name(priority: str | None) -> str:
    """Resolve a priority string to its arq queue name (default: normal)."""
    return QUEUE_NAMES.get(priority or "", DEFAULT_QUEUE)


async def _pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


async def enqueue_migration_job(job_id: int, priority: str | None = None) -> None:
    """Push a migration job onto the priority arq queue."""
    pool = await _pool()
    try:
        await pool.enqueue_job(
            "app.services.migration_service.run_migration_job",
            job_id,
            _queue_name=queue_name(priority),
        )
    finally:
        await pool.aclose()


async def enqueue_autonomous_migration(
    job_id: int,
    repo_url: str,
    repo_owner: str,
    repo_name: str,
    github_token: str,
    context_rule: str | None,
    base_branch: str,
    title: str | None = None,
    body: str | None = None,
    priority: str | None = None,
) -> None:
    """Push an autonomous git-driven migration job onto the priority queue."""
    pool = await _pool()
    try:
        await pool.enqueue_job(
            "app.services.orchestrator.run_autonomous_migration_job",
            job_id,
            repo_url,
            repo_owner,
            repo_name,
            github_token,
            context_rule,
            base_branch,
            title,
            body,
            _queue_name=queue_name(priority),
        )
    finally:
        await pool.aclose()
