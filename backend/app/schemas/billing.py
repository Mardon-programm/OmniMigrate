"""Billing schemas — plans, subscriptions, usage."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.billing import PlanInterval, SubscriptionStatus


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount_cents: int
    currency: str
    interval: PlanInterval
    max_jobs_per_month: int
    max_files_per_job: int
    max_llm_tokens_per_month: int
    max_org_members: int
    features: str | None = None
    is_active: bool


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    plan_id: int
    status: SubscriptionStatus
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime


class UsageRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    metric: str
    quantity: int
    recorded_at: datetime


class UsageSummary(BaseModel):
    metric: str
    current_usage: int
    limit: int
    period_start: datetime | None = None
    period_end: datetime | None = None


class CheckoutSessionRequest(BaseModel):
    plan_id: int
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    session_url: str


class WebhookResponse(BaseModel):
    received: bool = True


class UsageDashboardResponse(BaseModel):
    """Per-org usage dashboard with quota percentages."""

    organization_id: int
    plan_name: str
    period_start: datetime
    metrics: list[UsageMetricDetail]


class UsageMetricDetail(BaseModel):
    metric: str
    used: int
    limit: int
    percentage: float
    history: list[UsageDataPoint]


class UsageDataPoint(BaseModel):
    date: str
    count: int
