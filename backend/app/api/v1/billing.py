from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.billing import billing_service

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
async def paddle_webhook(request: Request):
    """Handle Paddle webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("paddle-signature") or request.headers.get("Paddle-Signature")

    event = billing_service.construct_webhook_event(payload, sig_header or "")
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    # Handle events
    event_type = event.get("event_type", "")

    if event_type == "transaction.completed":
        data = event.get("data", {})
        custom_data = data.get("custom_data", {})
        user_id = custom_data.get("user_id")
        # TODO: Update user subscription status in DB
        pass

    elif event_type == "subscription.cancelled":
        data = event.get("data", {})
        subscription_id = data.get("id")
        # TODO: Handle subscription cancellation
        pass

    elif event_type == "subscription.payment_failed":
        data = event.get("data", {})
        # TODO: Handle failed payment
        pass

    return {"status": "ok"}