"""Usage metrics tracking — records per-org consumption against plan quotas."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import LLM_CALLS, MIGRATION_TOTAL, SANDBOX_RUNS
from app.models.billing import UsageRecord

logger = structlog.get_logger(__name__)


async def record_usage(
    session: AsyncSession,
    org_id: int,
    metric: str,
    quantity: int = 1,
    subscription_id: int | None = None,
) -> None:
    """Write a usage record and update Prometheus counters."""
    record = UsageRecord(
        organization_id=org_id,
        metric=metric,
        quantity=quantity,
        subscription_id=subscription_id,
    )
    session.add(record)
    await session.flush()

    if metric == "jobs":
        MIGRATION_TOTAL.labels(status="submitted").inc()
    elif metric == "llm_tokens":
        LLM_CALLS.labels(provider="openai", status="success").inc()


async def get_usage_summary(
    session: AsyncSession,
    org_id: int,
    period_start: datetime | None = None,
) -> dict[str, int]:
    """Return aggregated usage counts for an organization."""
    start = period_start or _current_period_start()
    stmt = (
        select(UsageRecord.metric, func.sum(UsageRecord.quantity).label("total"))
        .where(UsageRecord.organization_id == org_id)
        .where(UsageRecord.recorded_at >= start)
        .group_by(UsageRecord.metric)
    )
    result = await session.execute(stmt)
    return {row.metric: int(row.total or 0) for row in result.all()}


async def check_quota(
    session: AsyncSession,
    org_id: int,
    metric: str,
    limit: int,
) -> tuple[bool, int]:
    """Check whether the org is within its quota. Returns (allowed, current_usage)."""
    usage = await get_usage_summary(session, org_id)
    current = usage.get(metric, 0)
    return current < limit, current


def _current_period_start() -> datetime:
    """Return the first day of the current month at midnight UTC."""
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def record_sandbox_result(success: bool) -> None:
    SANDBOX_RUNS.labels(result="pass" if success else "fail").inc()
