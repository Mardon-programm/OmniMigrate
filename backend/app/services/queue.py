from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings


async def enqueue_migration_job(job_id: int) -> None:
    """Push a migration job onto the arq queue for the worker to process."""
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("app.services.migration_service.run_migration_job", job_id)
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
) -> None:
    """Push an autonomous git-driven migration job onto the arq queue."""
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
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
        )
    finally:
        await pool.aclose()
