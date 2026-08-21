"""Tests for billing service and API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.billing import Plan, Subscription, SubscriptionStatus, UsageRecord
from app.models.organization import Organization
from app.services.billing import (
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
            json={"name": f"Billing Org {email}", "slug": email.split("@")[0].replace(".", "-")},
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

    async def test_checkout_no_stripe(self, client, db_session):
        await _seed_clean(db_session)
        org, h = await self._make_org(client, db_session, email="checkout@test.com")
        resp = await client.post(
            f"{BILLING_URL}/organizations/{org['id']}/checkout",
            json={"plan_id": 1, "success_url": "https://ok.com", "cancel_url": "https://no.com"},
            headers=h,
        )
        assert resp.status_code == 501
        assert "Stripe" in resp.json()["detail"]

    async def test_webhook_returns_received(self, client, db_session):
        resp = await client.post(f"{BILLING_URL}/webhook/stripe")
        assert resp.status_code == 200
        assert resp.json()["received"] is True
