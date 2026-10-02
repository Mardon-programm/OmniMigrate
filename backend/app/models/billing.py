"""Billing models — plans, subscriptions, usage metering."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanInterval(StrEnum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(StrEnum):
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    trialing = "trialing"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    paddle_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paddle_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    interval: Mapped[PlanInterval] = mapped_column(
        nullable=False,
        default=PlanInterval.monthly,
    )
    # Quotas
    max_jobs_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_files_per_job: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_llm_tokens_per_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100_000,
    )
    max_org_members: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("plans.id"),
        nullable=False,
        index=True,
    )
    paddle_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    paddle_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        nullable=False,
        default=SubscriptionStatus.trialing,
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    organization = relationship("Organization", backref="subscriptions")
    plan = relationship("Plan")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("subscriptions.id"),
        nullable=True,
        index=True,
    )
    metric: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # jobs, llm_tokens, files, member_days
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    subscription = relationship("Subscription")
