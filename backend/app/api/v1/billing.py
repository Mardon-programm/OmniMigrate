from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.organization import OrganizationMember
from app.services.billing import billing_service
from app.services.observability import (
    get_org_subscription,
    get_org_usage_details,
    list_plans,
)

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Paddle Checkout session for subscription."""
    url = await billing_service.create_checkout_session(
        user_id=str(current_user.id),
        user_email=current_user.email,
        price_id=request.price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing not configured",
        )
    return {"url": url}


@router.post("/portal")
async def create_portal(
    request: PortalRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Paddle Customer Portal session."""
    customer_id = await billing_service.get_customer_id(current_user.email)
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing account found",
        )

    url = await billing_service.create_billing_portal_session(
        customer_id=customer_id,
        return_url=request.return_url,
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing not configured",
        )
    return {"url": url}


@router.post("/webhook")
async def paddle_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Verify and apply a Paddle webhook event to subscriptions."""
    payload = await request.body()
    sig_header = request.headers.get("paddle-signature") or request.headers.get(
        "Paddle-Signature"
    )

    event = billing_service.construct_webhook_event(payload, sig_header or "")
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    applied = await billing_service.apply_webhook_event(db, event)
    return {"status": "ok", "applied": applied}


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    """List all available plans."""
    plans = await list_plans(db)
    return [
        {
            "id": p.id,
            "name": p.name,
            "amount_cents": p.amount_cents,
            "max_jobs_per_month": p.max_jobs_per_month,
            "max_files_per_job": p.max_files_per_job,
            "max_llm_tokens_per_month": p.max_llm_tokens_per_month,
            "features": p.features,
            "is_active": p.is_active,
        }
        for p in plans
    ]


@router.get("/organizations/{org_id}/subscription")
async def get_org_subscription_route(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization subscription."""
    # Verify user is member of org
    from sqlalchemy import select

    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    sub = await get_org_subscription(db, org_id)
    if not sub:
        return None
    return {
        "id": sub.id,
        "organization_id": sub.organization_id,
        "plan_id": sub.plan_id,
        "status": sub.status.value,
        "paddle_subscription_id": sub.paddle_subscription_id,
        "paddle_customer_id": sub.paddle_customer_id,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }


@router.get("/organizations/{org_id}/usage")
async def get_org_usage_route(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization usage details."""
    from sqlalchemy import select

    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    usage = await get_org_usage_details(db, org_id)
    return usage


class OrgCheckoutRequest(BaseModel):
    plan_id: int
    success_url: str
    cancel_url: str


@router.post("/organizations/{org_id}/checkout")
async def create_org_checkout(
    org_id: int,
    request: OrgCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a real Paddle checkout session for an organization plan."""
    if not billing_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Paddle billing not configured",
        )

    from sqlalchemy import select
    from app.models.billing import Plan

    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    plan = (
        await db.execute(
            select(Plan).where(Plan.id == request.plan_id, Plan.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.paddle_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plan has no Paddle price configured",
        )

    url = await billing_service.create_checkout_session(
        user_id=str(current_user.id),
        user_email=current_user.email,
        price_id=plan.paddle_price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={"organization_id": org_id, "plan_id": plan.id},
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to create Paddle checkout session",
        )
    return {"url": url}
