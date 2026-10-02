from __future__ import annotations

import hmac
import hashlib
import httpx
from typing import Optional

from app.core.config import settings


class BillingService:
    """Paddle billing service for subscriptions and checkout."""

    def __init__(self):
        self.enabled = bool(settings.paddle_api_key)
        self.api_key = settings.paddle_api_key
        self.webhook_secret = settings.paddle_webhook_secret
        self.vendor_id = settings.paddle_vendor_id
        self.base_url = "https://api.paddle.com" if settings.environment == "production" else "https://sandbox-api.paddle.com"

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
        self, customer_id: str, return_url: str
    ) -> Optional[str]:
        """Create a Paddle Customer Portal session for subscription management."""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/customers/{customer_id}/portal-session",
                    headers=self._headers(),
                    json={"return_url": return_url},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"]["url"]
        except httpx.HTTPError:
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
        """Cancel a subscription at period end."""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/subscriptions/{subscription_id}",
                    headers=self._headers(),
                    json={"status": "paused"},
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    def construct_webhook_event(self, payload: bytes, sig_header: str):
        """Verify and construct webhook event."""
        if not self.enabled or not self.webhook_secret:
            return None

        try:
            # Paddle uses HMAC-SHA256 for webhook verification
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_sig, sig_header):
                return None

            import json
            return json.loads(payload.decode())
        except Exception:
            return None


billing_service = BillingService()