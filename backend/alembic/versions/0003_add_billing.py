"""Add billing: plans, subscriptions, usage records + seed default plans.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UNLIMITED = -1


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column("stripe_product_id", sa.String(255), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("interval", sa.String(32), nullable=False, server_default="monthly"),
        sa.Column("max_jobs_per_month", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_files_per_job", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "max_llm_tokens_per_month", sa.Integer(), nullable=False, server_default="100000"
        ),
        sa.Column("max_org_members", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_plans_id", "plans", ["id"])
    op.create_index("ix_plans_name", "plans", ["name"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("plans.id"),
            nullable=False,
        ),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="trialing"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"])
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("subscriptions.id"),
            nullable=True,
        ),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_records_id", "usage_records", ["id"])
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_subscription_id", "usage_records", ["subscription_id"])
    op.create_index("ix_usage_records_metric", "usage_records", ["metric"])
    op.create_index("ix_usage_records_recorded_at", "usage_records", ["recorded_at"])

    _seed_default_plans()


def _seed_default_plans() -> None:
    plans_table = sa.Table(
        "plans",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100)),
        sa.Column("amount_cents", sa.Integer()),
        sa.Column("currency", sa.String(3)),
        sa.Column("interval", sa.String(32)),
        sa.Column("max_jobs_per_month", sa.Integer()),
        sa.Column("max_files_per_job", sa.Integer()),
        sa.Column("max_llm_tokens_per_month", sa.Integer()),
        sa.Column("max_org_members", sa.Integer()),
        sa.Column("features", sa.Text()),
        sa.Column("is_active", sa.Boolean()),
        schema=None,
    )

    op.bulk_insert(
        plans_table,
        [
            {
                "name": "Free",
                "amount_cents": 0,
                "currency": "usd",
                "interval": "monthly",
                "max_jobs_per_month": 10,
                "max_files_per_job": 50,
                "max_llm_tokens_per_month": 100_000,
                "max_org_members": 5,
                "features": '{"support": "community"}',
                "is_active": True,
            },
            {
                "name": "Team",
                "amount_cents": 4900,
                "currency": "usd",
                "interval": "monthly",
                "max_jobs_per_month": 100,
                "max_files_per_job": 500,
                "max_llm_tokens_per_month": 2_000_000,
                "max_org_members": 25,
                "features": '{"support": "priority", "git_integration": true}',
                "is_active": True,
            },
            {
                "name": "Enterprise",
                "amount_cents": 19900,
                "currency": "usd",
                "interval": "monthly",
                "max_jobs_per_month": UNLIMITED,
                "max_files_per_job": UNLIMITED,
                "max_llm_tokens_per_month": UNLIMITED,
                "max_org_members": UNLIMITED,
                "features": '{"support": "dedicated", "git_integration": true, "sla": true}',
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("plans")
