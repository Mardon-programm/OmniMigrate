"""Billing service — plan management, usage metering, quota enforcement."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import (
    Plan,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)


async def list_plans(db: AsyncSession) -> Sequence[Plan]:
    stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.amount_cents)  # noqa: E712
    return (await db.execute(stmt)).scalars().all()


async def get_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    return await db.get(Plan, plan_id)


async def get_org_subscription(
    db: AsyncSession,
    org_id: int,
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(
            Subscription.organization_id == org_id,
            Subscription.status.in_(
                [
                    SubscriptionStatus.active,
                    SubscriptionStatus.trialing,
                ]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def record_usage(
    db: AsyncSession,
    *,
    org_id: int,
    subscription_id: int | None,
    metric: str,
    quantity: int = 1,
) -> UsageRecord:
    entry = UsageRecord(
        organization_id=org_id,
        subscription_id=subscription_id,
        metric=metric,
        quantity=quantity,
    )
    db.add(entry)
    return entry


async def get_usage_summary(
    db: AsyncSession,
    org_id: int,
    metric: str,
    period_start: datetime | None = None,
) -> int:
    stmt = select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
        UsageRecord.organization_id == org_id,
        UsageRecord.metric == metric,
    )
    if period_start is not None:
        stmt = stmt.where(UsageRecord.recorded_at >= period_start)
    return (await db.execute(stmt)).scalar_one()


async def check_quota(
    db: AsyncSession,
    org_id: int,
    metric: str,
    limit: int,
    period_days: int = 30,
) -> bool:
    """Returns True if within quota (not exceeded)."""
    period_start = datetime.now(UTC) - timedelta(days=period_days)
    usage = await get_usage_summary(db, org_id, metric, period_start)
    return usage < limit


async def get_org_usage_details(
    db: AsyncSession,
    org_id: int,
    period_days: int = 30,
) -> dict[str, int]:
    period_start = datetime.now(UTC) - timedelta(days=period_days)
    metrics = ["jobs", "llm_tokens", "files"]
    result: dict[str, int] = {}
    for m in metrics:
        result[m] = await get_usage_summary(db, org_id, m, period_start)
    return result
