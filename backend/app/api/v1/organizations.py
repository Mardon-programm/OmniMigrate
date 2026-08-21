from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User, UserRole
from app.schemas.organization import (
    AuditLogRead,
    OrgCreate,
    OrgMemberInvite,
    OrgMemberRead,
    OrgMemberUpdate,
    OrgRead,
    OrgUpdate,
)
from app.services.audit_log import list_audit_logs, log_event
from app.services.rbac import get_org_role, has_min_role

router = APIRouter()


async def _get_org(org_id: int, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def _require_org_member(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Organization, OrgRole | None]:
    org = await _get_org(org_id, db)
    role = await get_org_role(db, user.id, org.id)
    return user, org, role


async def _require_org_admin(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Organization, OrgRole]:
    user, org, role = await _require_org_member(org_id, user, db)
    if user.role == UserRole.admin:
        if role is None:
            role = OrgRole.admin
        return user, org, role
    if not has_min_role(role, OrgRole.admin):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user, org, role  # type: ignore[return-value]


@router.post("/", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrgCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Organization).where(Organization.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Slug already taken")
    org = Organization(name=body.name, slug=body.slug, description=body.description)
    db.add(org)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Slug or name already taken") from None
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.owner,
    )
    db.add(member)
    await db.flush()
    await log_event(
        db,
        action="org.create",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=user.id,
        organization_id=org.id,
    )
    await db.commit()
    return org


@router.get("/{org_id}", response_model=OrgRead)
async def get_organization(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, role = await _require_org_member(org_id, user, db)
    if role is None and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not a member")
    return org


@router.patch("/{org_id}", response_model=OrgRead)
async def update_organization(
    org_id: int,
    body: OrgUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, _ = await _require_org_admin(org_id, user, db)
    if body.name is not None:
        org.name = body.name
    if body.description is not None:
        org.description = body.description
    if body.is_active is not None:
        org.is_active = body.is_active
    await db.flush()
    await log_event(
        db,
        action="org.update",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=user.id,
        organization_id=org.id,
    )
    await db.commit()
    return org


@router.post(
    "/{org_id}/members",
    response_model=OrgMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: int,
    body: OrgMemberInvite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, _ = await _require_org_admin(org_id, user, db)
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == body.user_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already a member")
    member = OrganizationMember(
        organization_id=org.id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(member)
    await db.flush()
    await log_event(
        db,
        action="org.member.add",
        resource_type="organization_member",
        resource_id=str(org.id),
        detail=f"user_id={body.user_id} role={body.role.value}",
        user_id=user.id,
        organization_id=org.id,
    )
    await db.commit()
    return member


@router.get("/{org_id}/members", response_model=list[OrgMemberRead])
async def list_members(
    org_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, role = await _require_org_member(org_id, user, db)
    if role is None and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not a member")
    stmt = select(OrganizationMember).where(OrganizationMember.organization_id == org.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{org_id}/members/{member_id}", response_model=OrgMemberRead)
async def update_member(
    org_id: int,
    member_id: int,
    body: OrgMemberUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, _ = await _require_org_admin(org_id, user, db)
    stmt = select(OrganizationMember).where(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org.id,
    )
    member = (await db.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if body.role is not None:
        member.role = body.role
    if body.is_active is not None:
        member.is_active = body.is_active
    await db.flush()
    await log_event(
        db,
        action="org.member.update",
        resource_type="organization_member",
        resource_id=str(member_id),
        user_id=user.id,
        organization_id=org.id,
    )
    await db.commit()
    return member


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, _ = await _require_org_admin(org_id, user, db)
    stmt = select(OrganizationMember).where(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org.id,
    )
    member = (await db.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == OrgRole.owner:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    await db.delete(member)
    await log_event(
        db,
        action="org.member.remove",
        resource_type="organization_member",
        resource_id=str(member_id),
        user_id=user.id,
        organization_id=org.id,
    )
    await db.commit()


@router.get("/{org_id}/audit-logs", response_model=list[AuditLogRead])
async def get_audit_logs(
    org_id: int,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, org, role = await _require_org_member(org_id, user, db)
    if role is None and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not a member")
    return await list_audit_logs(db, organization_id=org.id, limit=limit, offset=offset)
