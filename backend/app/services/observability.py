"""Usage metrics tracking — records per-org consumption against plan quotas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import overload

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import LLM_CALLS, MIGRATION_TOTAL, SANDBOX_RUNS
from app.models.billing import Plan, Subscription, SubscriptionStatus, UsageRecord

logger = structlog.get_logger(__name__)


async def record_usage(
    session: AsyncSession,
    org_id: int,
    metric: str,
    quantity: int = 1,
    subscription_id: int | None = None,
) -> UsageRecord:
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

    return record


@overload
async def get_usage_summary(
    session: AsyncSession,
    org_id: int,
    metric: str,
    period_start: datetime | None = None,
) -> int: ...


@overload
async def get_usage_summary(
    session: AsyncSession,
    org_id: int,
    metric: None = None,
    period_start: datetime | None = None,
) -> dict[str, int]: ...


async def get_usage_summary(
    session: AsyncSession,
    org_id: int,
    metric: str | None = None,
    period_start: datetime | None = None,
) -> int | dict[str, int]:
    """Return aggregated usage counts for an organization."""
    start = period_start or _current_period_start()
    stmt = (
        select(UsageRecord.metric, func.sum(UsageRecord.quantity).label("total"))
        .where(UsageRecord.organization_id == org_id)
        .where(UsageRecord.recorded_at >= start)
        .group_by(UsageRecord.metric)
    )
    result = await session.execute(stmt)
    usage = {row.metric: int(row.total or 0) for row in result.all()}
    if metric:
        return usage.get(metric, 0)
    return usage


async def check_quota(
    session: AsyncSession,
    org_id: int,
    metric: str,
    limit: int,
) -> bool:
    """Check whether the org is within its quota."""
    usage = await get_usage_summary(session, org_id, metric)
    return usage < limit


def _current_period_start() -> datetime:
    """Return the first day of the current month at midnight UTC."""
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def record_sandbox_result(success: bool) -> None:
    SANDBOX_RUNS.labels(result="pass" if success else "fail").inc()


async def list_plans(session: AsyncSession) -> list[Plan]:
    """Return all active plans."""
    stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.amount_cents)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_org_subscription(
    session: AsyncSession, org_id: int
) -> Subscription | None:
    """Return the active subscription for an organization."""
    stmt = (
        select(Subscription)
        .where(Subscription.organization_id == org_id)
        .where(Subscription.status == SubscriptionStatus.active)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_org_usage_details(session: AsyncSession, org_id: int) -> dict[str, int]:
    """Return all usage metrics for an organization (current period)."""
    usage = await get_usage_summary(session, org_id)
    # Ensure all expected metrics are present
    return {
        "jobs": usage.get("jobs", 0),
        "llm_tokens": usage.get("llm_tokens", 0),
        "files": usage.get("files", 0),
    }
