"""Billing API — plans, subscriptions, usage, Stripe checkout."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import UserRole
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PlanRead,
    SubscriptionRead,
    WebhookResponse,
)
from app.services.billing import (
    get_org_subscription,
    get_org_usage_details,
    list_plans,
)

router = APIRouter()


async def _require_org_admin(
    org_id: int,
    user: CurrentUser,
    db: DbSession,
) -> tuple[Organization, OrgRole]:
    if user.role == UserRole.admin:
        stmt = select(Organization).where(Organization.id == org_id)
        org = (await db.execute(stmt)).scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org, OrgRole.admin
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True,  # noqa: E712
    )
    member = (await db.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    from app.services.rbac import has_min_role

    if not has_min_role(member.role, OrgRole.admin):
        raise HTTPException(status_code=403, detail="Admin role required")
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org, member.role


@router.get("/plans", response_model=list[PlanRead])
async def get_plans(db: DbSession):
    return await list_plans(db)


@router.get(
    "/organizations/{org_id}/subscription",
    response_model=SubscriptionRead | None,
)
async def get_subscription(
    org_id: int,
    user: CurrentUser,
    db: DbSession,
):
    await _require_org_admin(org_id, user, db)
    return await get_org_subscription(db, org_id)


@router.get(
    "/organizations/{org_id}/usage",
    response_model=dict[str, int],
)
async def get_usage(
    org_id: int,
    user: CurrentUser,
    db: DbSession,
):
    await _require_org_admin(org_id, user, db)
    return await get_org_usage_details(db, org_id)


@router.post(
    "/organizations/{org_id}/checkout",
    response_model=CheckoutSessionResponse,
)
async def create_checkout(
    org_id: int,
    body: CheckoutSessionRequest,
    user: CurrentUser,
    db: DbSession,
):
    await _require_org_admin(org_id, user, db)
    # In production, this would create a Stripe Checkout Session.
    # For now, return a placeholder URL.
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=501,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY.",
        )
    return CheckoutSessionResponse(
        session_url=f"https://checkout.stripe.com/pay/cs_placeholder_org{org_id}_plan{body.plan_id}",
    )


@router.post("/webhook/stripe", response_model=WebhookResponse)
async def stripe_webhook(request: Request, db: DbSession):
    """Handle Stripe webhook events (subscription updates, invoices, etc.)."""
    _body = await request.body()
    # In production: verify Stripe signature, parse event, update subscription.
    # For now, accept and acknowledge.
    return WebhookResponse(received=True)
