"""RBAC service — organization-level role-based access control."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationMember, OrgRole


async def get_org_role(db: AsyncSession, user_id: int, organization_id: int) -> OrgRole | None:
    stmt = select(OrganizationMember).where(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    return member.role if member else None


ORG_ROLE_HIERARCHY: dict[OrgRole, int] = {
    OrgRole.owner: 30,
    OrgRole.admin: 20,
    OrgRole.member: 10,
    OrgRole.viewer: 0,
}


def has_min_role(user_role: OrgRole | None, required: OrgRole) -> bool:
    if user_role is None:
        return False
    return ORG_ROLE_HIERARCHY[user_role] >= ORG_ROLE_HIERARCHY[required]
