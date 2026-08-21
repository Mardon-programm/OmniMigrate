"""Audit log service — records who did what, when, on which resource."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import AuditLog


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    user_id: int | None = None,
    organization_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        user_id=user_id,
        organization_id=organization_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if organization_id is not None:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
