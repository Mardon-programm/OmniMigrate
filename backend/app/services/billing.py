from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class BillingService:
    """Paddle billing service for subscriptions and checkout."""

    def __init__(self):
        self.enabled = bool(settings.paddle_api_key)
        self.api_key = settings.paddle_api_key
        self.webhook_secret = settings.paddle_webhook_secret
        self.vendor_id = settings.paddle_vendor_id
        self.base_url = (
            "https://api.paddle.com"
            if settings.environment == "production"
            else "https://sandbox-api.paddle.com"
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """Create a Paddle Checkout session for subscription."""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transactions",
                    headers=self._headers(),
                    json={
                        "items": [{"price_id": price_id, "quantity": 1}],
                        "checkout": {
                            "success_url": success_url,
                            "cancel_url": cancel_url,
                        },
                        "customer": {"email": user_email},
                        "custom_data": {"user_id": user_id, **(metadata or {})},
                        "recurring": True,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"]["checkout"]["url"]
        except httpx.HTTPError:
            return None

    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
        subscription_ids: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Create a Paddle Customer Portal session for subscription management.

        ``return_url`` is kept for caller compatibility; Paddle's portal-session
        endpoint does not accept it and configures return behaviour elsewhere.
        """
        if not self.enabled:
            return None

        body: dict = {}
        if subscription_ids:
            body["subscription_ids"] = subscription_ids

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/customers/{customer_id}/portal-sessions",
                    headers=self._headers(),
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                url = data["data"]["urls"]["general"]["overview"]
                if url.startswith("//"):
                    return f"https:{url}"
                if not url.startswith(("http://", "https://")):
                    return f"https://{url}"
                return url
        except (httpx.HTTPError, KeyError, TypeError, AttributeError):
            return None

    async def get_customer_id(self, email: str) -> Optional[str]:
        """Get or create a Paddle customer by email."""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient() as client:
                # Search for existing customer
                response = await client.get(
                    f"{self.base_url}/customers",
                    headers=self._headers(),
                    params={"email": email},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                if data["data"]:
                    return data["data"][0]["id"]

                # Create new customer
                response = await client.post(
                    f"{self.base_url}/customers",
                    headers=self._headers(),
                    json={"email": email},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"]["id"]
        except httpx.HTTPError:
            return None

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription at period end without pausing it."""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/subscriptions/{subscription_id}/cancel",
                    headers=self._headers(),
                    json={"effective_from": "next_billing_period"},
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    # Paddle SDKs default to a five-second tolerance. Allow a little more for
    # clock skew and delivery retries, while still rejecting stale replays.
    WEBHOOK_TOLERANCE_SECONDS = 300

    def construct_webhook_event(
        self, payload: bytes, sig_header: str
    ) -> Optional[dict]:
        """Verify a Paddle ``Paddle-Signature`` header and parse the raw body.

        Paddle signs ``"{ts}:{raw_body}"`` with HMAC-SHA256. During secret
        rotation the header can contain several ``h1`` values; any match is
        valid. The raw body must be passed through unchanged.
        """
        if not self.enabled or not self.webhook_secret or not payload or not sig_header:
            return None

        try:
            parts: dict[str, list[str]] = {}
            for part in sig_header.split(";"):
                key, separator, value = part.strip().partition("=")
                if not separator or not key or not value:
                    return None
                parts.setdefault(key, []).append(value)

            timestamps = parts.get("ts", [])
            signatures = parts.get("h1", [])
            if len(timestamps) != 1 or not signatures:
                return None

            timestamp = timestamps[0]
            if not timestamp.isdigit():
                return None
            if abs(time.time() - int(timestamp)) > self.WEBHOOK_TOLERANCE_SECONDS:
                return None

            signed_payload = timestamp.encode("utf-8") + b":" + payload
            expected_sig = hmac.new(
                self.webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
            ).hexdigest()
            if not any(
                hmac.compare_digest(expected_sig, signature) for signature in signatures
            ):
                return None

            event = json.loads(payload.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return None

        return event if isinstance(event, dict) else None

    @classmethod
    def _billing_period(
        cls, data: dict
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """Read period boundaries from both legacy and Paddle-native fields."""
        period = data.get("current_billing_period") or {}
        if not isinstance(period, dict):
            period = {}
        start = cls._parse_datetime(
            data.get("current_period_start")
        ) or cls._parse_datetime(period.get("starts_at"))
        end = cls._parse_datetime(
            data.get("current_period_end")
        ) or cls._parse_datetime(period.get("ends_at"))
        return start, end

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _map_status(value: str):
        from app.models.billing import SubscriptionStatus

        normalized = (value or "").lower()
        if normalized in {"active", "trialing"}:
            return (
                SubscriptionStatus.active
                if normalized == "active"
                else SubscriptionStatus.trialing
            )
        if normalized in {"past_due", "paused"}:
            return SubscriptionStatus.past_due
        if normalized in {"canceled", "cancelled"}:
            return SubscriptionStatus.canceled
        return None

    async def apply_webhook_event(self, session: AsyncSession, event: dict) -> bool:
        """Persist the effect of a verified Paddle webhook event.

        Returns True when a plan/subscription was actually changed. Unknown
        events are acknowledged (False) so Paddle does not endlessly retry.
        """
        from app.models.billing import Plan, Subscription, SubscriptionStatus

        event_type = event.get("event_type", "")
        data = event.get("data") or {}
        if not isinstance(data, dict):
            return False
        custom = data.get("custom_data") or {}
        if not isinstance(custom, dict):
            custom = {}

        if event_type == "transaction.completed":
            org_id = custom.get("organization_id") or custom.get("org_id")
            if not org_id:
                return False

            price_id = None
            items = data.get("items") or []
            if items and isinstance(items[0], dict):
                price_id = items[0].get("price_id")

            stmt = select(Plan).where(Plan.is_active.is_(True))
            if price_id:
                stmt = stmt.where(Plan.paddle_price_id == price_id)
            elif custom.get("plan_id"):
                stmt = stmt.where(Plan.id == int(custom["plan_id"]))
            else:
                return False
            plan = (await session.execute(stmt)).scalar_one_or_none()
            if not plan:
                return False

            paddle_subscription_id = data.get("subscription_id")
            if paddle_subscription_id:
                sub = (
                    await session.execute(
                        select(Subscription).where(
                            Subscription.paddle_subscription_id
                            == paddle_subscription_id
                        )
                    )
                ).scalar_one_or_none()
            else:
                sub = None

            if not sub:
                sub = Subscription(
                    organization_id=int(org_id),
                    plan_id=plan.id,
                    paddle_subscription_id=paddle_subscription_id,
                )
                session.add(sub)

            sub.plan_id = plan.id
            sub.status = SubscriptionStatus.active
            sub.paddle_customer_id = data.get("customer_id") or sub.paddle_customer_id
            period_start, period_end = self._billing_period(data)
            sub.current_period_start = period_start or sub.current_period_start
            sub.current_period_end = period_end or sub.current_period_end
            await session.commit()
            return True

        if event_type.startswith("subscription."):
            paddle_subscription_id = data.get("id")
            if not paddle_subscription_id:
                return False
            sub = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.paddle_subscription_id == paddle_subscription_id
                    )
                )
            ).scalar_one_or_none()
            if not sub:
                return False

            status = self._map_status(data.get("status", ""))
            if status:
                sub.status = status
            if event_type in {"subscription.canceled", "subscription.cancelled"}:
                sub.cancel_at_period_end = True
            elif event_type == "subscription.resumed":
                sub.cancel_at_period_end = False
            period_start, period_end = self._billing_period(data)
            sub.current_period_start = period_start or sub.current_period_start
            sub.current_period_end = period_end or sub.current_period_end
            await session.commit()
            return True

        return False


billing_service = BillingService()
