"""Tests for billing service and API endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

import httpx

from app.models.billing import Plan, Subscription, SubscriptionStatus, UsageRecord
from app.models.organization import Organization
from app.services.observability import (
    check_quota,
    get_org_subscription,
    get_org_usage_details,
    get_usage_summary,
    list_plans,
    record_usage,
)
from sqlalchemy import text
from tests.conftest import auth_headers, make_user

BILLING_URL = "/api/v1/billing"
ORG_URL = "/api/v1/organizations/"

_org_counter = 0


class _StubAsyncClient:
    """Capture Paddle API calls without making network requests."""

    def __init__(self, handler, calls):
        self.handler = handler
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs["json"]))
        return self.handler(url, **kwargs)


async def _make_org(db, name="Billing Org", slug="billing-org"):
    global _org_counter
    _org_counter += 1
    org = Organization(name=f"{name} {_org_counter}", slug=f"{slug}-{_org_counter}")
    db.add(org)
    await db.flush()
    return org


async def _seed_clean(db):
    await db.execute(text("DELETE FROM usage_records"))
    await db.execute(text("DELETE FROM subscriptions"))
    await db.execute(text("DELETE FROM plans"))
    await db.execute(text("DELETE FROM organization_members"))
    await db.execute(text("DELETE FROM organizations"))
    await db.commit()


class TestBillingService:
    async def test_list_plans(self, db_session):
        await _seed_clean(db_session)
        p1 = Plan(name="Free", amount_cents=0, max_jobs_per_month=10)
        p2 = Plan(name="Team", amount_cents=4900, max_jobs_per_month=100)
        db_session.add_all([p1, p2])
        await db_session.commit()
        plans = await list_plans(db_session)
        assert len(plans) >= 2
        names = {p.name for p in plans}
        assert "Free" in names
        assert "Team" in names

    async def test_list_plans_excludes_inactive(self, db_session):
        await _seed_clean(db_session)
        active = Plan(name="ActivePlan", amount_cents=100, is_active=True)
        inactive = Plan(name="InactivePlan", amount_cents=200, is_active=False)
        db_session.add_all([active, inactive])
        await db_session.commit()
        plans = await list_plans(db_session)
        names = {p.name for p in plans}
        assert "ActivePlan" in names
        assert "InactivePlan" not in names

    async def test_get_org_subscription(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Sub Org", slug="sub-org")
        plan = Plan(name="SubPlan", amount_cents=1000)
        db_session.add(plan)
        await db_session.flush()
        sub = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.active,
        )
        db_session.add(sub)
        await db_session.commit()
        result = await get_org_subscription(db_session, org.id)
        assert result is not None
        assert result.organization_id == org.id

    async def test_get_org_subscription_none(self, db_session):
        result = await get_org_subscription(db_session, 99999)
        assert result is None

    async def test_record_usage(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Usage Org", slug="usage-org")
        await db_session.commit()
        entry = await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=1,
        )
        assert entry.metric == "jobs"
        assert entry.quantity == 1

    async def test_apply_webhook_activates_subscription(self, db_session):
        from app.services.billing import billing_service

        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Webhook Org", slug="webhook-org")
        plan = Plan(
            name="ProWebhook",
            amount_cents=7900,
            paddle_price_id="pri_test_pro",
            max_jobs_per_month=100,
        )
        db_session.add(plan)
        await db_session.flush()

        event = {
            "event_type": "transaction.completed",
            "data": {
                "subscription_id": "sub_test_1",
                "customer_id": "ctm_test_1",
                "items": [{"price_id": "pri_test_pro"}],
                "custom_data": {"organization_id": org.id, "plan_id": plan.id},
                "current_period_end": "2026-12-31T00:00:00Z",
            },
        }
        applied = await billing_service.apply_webhook_event(db_session, event)

        assert applied is True
        sub = await get_org_subscription(db_session, org.id)
        assert sub is not None
        assert sub.status == SubscriptionStatus.active
        assert sub.paddle_subscription_id == "sub_test_1"

    def test_construct_webhook_event_verifies_paddle_signature(self, monkeypatch):
        from app.services.billing import billing_service

        secret = "pdl_ntfset_test_secret"
        monkeypatch.setattr(billing_service, "enabled", True)
        monkeypatch.setattr(billing_service, "webhook_secret", secret)

        payload = b'{"event_type":"transaction.completed","data":{"id":"txn_1"}}'
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}:".encode() + payload
        signature = hmac.new(
            secret.encode(), signed_payload, hashlib.sha256
        ).hexdigest()
        # Paddle sends more than one h1 during secret rotation.
        header = f"ts={timestamp};h1=deadbeef;h1={signature}"

        assert billing_service.construct_webhook_event(payload, header) == json.loads(
            payload
        )
        assert (
            billing_service.construct_webhook_event(
                payload, f"ts={timestamp};h1=deadbeef"
            )
            is None
        )

        stale_timestamp = str(
            int(time.time()) - billing_service.WEBHOOK_TOLERANCE_SECONDS - 10
        )
        stale_signature = hmac.new(
            secret.encode(), f"{stale_timestamp}:".encode() + payload, hashlib.sha256
        ).hexdigest()
        assert (
            billing_service.construct_webhook_event(
                payload, f"ts={stale_timestamp};h1={stale_signature}"
            )
            is None
        )
        # The signed body is byte-exact; trailing whitespace invalidates it.
        assert billing_service.construct_webhook_event(payload + b" ", header) is None

    async def test_portal_session_uses_paddle_endpoint_and_response(self, monkeypatch):
        from app.services import billing as billing_module
        from app.services.billing import billing_service

        calls: list[tuple[str, dict]] = []

        def handler(url, **kwargs):
            return httpx.Response(
                201,
                json={
                    "data": {
                        "urls": {
                            "general": {
                                "overview": "customer-portal.paddle.com/session"
                            }
                        }
                    }
                },
                request=httpx.Request("POST", url),
            )

        def client_factory():
            return _StubAsyncClient(handler, calls)

        monkeypatch.setattr(billing_module.httpx, "AsyncClient", client_factory)
        monkeypatch.setattr(billing_service, "enabled", True)

        url = await billing_service.create_billing_portal_session(
            "ctm_test", "https://app.example/return", ["sub_test"]
        )

        assert url == "https://customer-portal.paddle.com/session"
        assert calls[0][0].endswith("/customers/ctm_test/portal-sessions")
        assert calls[0][1] == {"subscription_ids": ["sub_test"]}

    async def test_cancel_subscription_uses_paddle_cancel_endpoint(self, monkeypatch):
        from app.services import billing as billing_module
        from app.services.billing import billing_service

        calls: list[tuple[str, dict]] = []

        def handler(url, **kwargs):
            return httpx.Response(
                200,
                json={"data": {"id": "sub_test"}},
                request=httpx.Request("POST", url),
            )

        def client_factory():
            return _StubAsyncClient(handler, calls)

        monkeypatch.setattr(billing_module.httpx, "AsyncClient", client_factory)
        monkeypatch.setattr(billing_service, "enabled", True)

        assert await billing_service.cancel_subscription("sub_test") is True
        assert calls[0][0].endswith("/subscriptions/sub_test/cancel")
        assert calls[0][1] == {"effective_from": "next_billing_period"}

    async def test_apply_webhook_uses_paddle_billing_period(self, db_session):
        from app.services.billing import billing_service

        await _seed_clean(db_session)
        org = await _make_org(
            db_session, name="Period Webhook Org", slug="period-webhook-org"
        )
        plan = Plan(
            name="PeriodPro",
            amount_cents=7900,
            paddle_price_id="pri_period_pro",
        )
        db_session.add(plan)
        await db_session.flush()

        event = {
            "event_type": "transaction.completed",
            "data": {
                "subscription_id": "sub_period_1",
                "items": [{"price_id": "pri_period_pro"}],
                "custom_data": {"organization_id": org.id},
                "current_billing_period": {
                    "starts_at": "2026-11-01T00:00:00Z",
                    "ends_at": "2026-12-01T00:00:00Z",
                },
            },
        }
        assert await billing_service.apply_webhook_event(db_session, event) is True
        sub = await get_org_subscription(db_session, org.id)
        assert sub is not None
        assert sub.current_period_start is not None
        assert sub.current_period_end is not None
        # SQLite drops tzinfo even though the column is timezone-aware.
        assert sub.current_period_start.replace(tzinfo=None) == datetime(2026, 11, 1)
        assert sub.current_period_end.replace(tzinfo=None) == datetime(2026, 12, 1)

    async def test_get_usage_summary(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Summary Org", slug="summary-org")
        await db_session.commit()
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=3,
        )
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=2,
        )
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="llm_tokens",
            quantity=100,
        )
        await db_session.commit()
        total = await get_usage_summary(db_session, org.id, "jobs")
        assert total == 5
        tokens = await get_usage_summary(db_session, org.id, "llm_tokens")
        assert tokens == 100

    async def test_get_usage_summary_with_period(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Period Org", slug="period-org")
        await db_session.commit()
        old_time = datetime.now(UTC) - timedelta(days=60)
        entry = UsageRecord(
            organization_id=org.id,
            metric="jobs",
            quantity=5,
            recorded_at=old_time,
        )
        db_session.add(entry)
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=2,
        )
        await db_session.commit()
        period_start = datetime.now(UTC) - timedelta(days=30)
        total = await get_usage_summary(db_session, org.id, "jobs", period_start)
        assert total == 2

    async def test_check_quota_within_limit(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Quota Org", slug="quota-org")
        await db_session.commit()
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=5,
        )
        await db_session.commit()
        assert await check_quota(db_session, org.id, "jobs", limit=10) is True

    async def test_check_quota_exceeded(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Exceed Org", slug="exceed-org")
        await db_session.commit()
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=10,
        )
        await db_session.commit()
        assert await check_quota(db_session, org.id, "jobs", limit=10) is False

    async def test_get_org_usage_details(self, db_session):
        await _seed_clean(db_session)
        org = await _make_org(db_session, name="Details Org", slug="details-org")
        await db_session.commit()
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="jobs",
            quantity=3,
        )
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="llm_tokens",
            quantity=500,
        )
        await record_usage(
            db_session,
            org_id=org.id,
            subscription_id=None,
            metric="files",
            quantity=12,
        )
        await db_session.commit()
        details = await get_org_usage_details(db_session, org.id)
        assert details["jobs"] == 3
        assert details["llm_tokens"] == 500
        assert details["files"] == 12


class TestBillingAPI:
    async def _make_org(self, client, db, email="bill@test.com"):
        user = await make_user(db, email=email, role="engineer")
        h = auth_headers(user.id)
        resp = await client.post(
            ORG_URL,
            json={
                "name": f"Billing Org {email}",
                "slug": email.split("@")[0].replace(".", "-"),
            },
            headers=h,
        )
        assert resp.status_code == 201
        org = resp.json()
        return org, h

    async def test_list_plans_empty(self, client, db_session):
        await _seed_clean(db_session)
        resp = await client.get(f"{BILLING_URL}/plans")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_plans(self, client, db_session):
        await _seed_clean(db_session)
        plan = Plan(name="TestPlan", amount_cents=999, max_jobs_per_month=50)
        db_session.add(plan)
        await db_session.commit()
        resp = await client.get(f"{BILLING_URL}/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["name"] == "TestPlan" for p in data)

    async def test_get_subscription(self, client, db_session):
        await _seed_clean(db_session)
        org, h = await self._make_org(client, db_session, email="sub.api@test.com")
        resp = await client.get(
            f"{BILLING_URL}/organizations/{org['id']}/subscription",
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_get_usage(self, client, db_session):
        await _seed_clean(db_session)
        org, h = await self._make_org(client, db_session, email="usage.api@test.com")
        resp = await client.get(
            f"{BILLING_URL}/organizations/{org['id']}/usage",
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert "llm_tokens" in data
        assert "files" in data

    async def test_checkout_no_stripe(self, client, db_session, monkeypatch):
        # Make the test independent of whatever PADDLE_* keys happen to be in .env.
        from app.services.billing import billing_service

        monkeypatch.setattr(billing_service, "enabled", False)
        await _seed_clean(db_session)
        org, h = await self._make_org(client, db_session, email="checkout@test.com")
        resp = await client.post(
            f"{BILLING_URL}/organizations/{org['id']}/checkout",
            json={
                "plan_id": 1,
                "success_url": "https://ok.com",
                "cancel_url": "https://no.com",
            },
            headers=h,
        )
        assert resp.status_code == 501
        assert "Paddle" in resp.json()["detail"]

    async def test_webhook_rejects_invalid_signature(
        self, client, db_session, monkeypatch
    ):
        from app.services.billing import billing_service

        monkeypatch.setattr(billing_service, "enabled", False)
        resp = await client.post(
            f"{BILLING_URL}/webhook",
            json={"event_type": "transaction.completed", "data": {}},
            headers={"Paddle-Signature": "ts=1;h1=invalid"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid webhook signature"
