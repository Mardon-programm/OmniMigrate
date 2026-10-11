"""Add migration packs for pay-as-you-go pricing

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "migration_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("migrations_count", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_migration_packs_id", "migration_packs", ["id"])
    op.create_index("ix_migration_packs_name", "migration_packs", ["name"], unique=True)

    # Seed default packs
    packs_table = sa.Table(
        "migration_packs",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50)),
        sa.Column("display_name", sa.String(100)),
        sa.Column("migrations_count", sa.Integer()),
        sa.Column("price_cents", sa.Integer()),
        sa.Column("currency", sa.String(3)),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("sort_order", sa.Integer()),
        schema=None,
    )

    op.bulk_insert(
        packs_table,
        [
            {
                "name": "pack_10",
                "display_name": "Pack 10",
                "migrations_count": 10,
                "price_cents": 500,
                "currency": "usd",
                "is_active": True,
                "sort_order": 1,
            },
            {
                "name": "pack_50",
                "display_name": "Pack 50",
                "migrations_count": 50,
                "price_cents": 1900,
                "currency": "usd",
                "is_active": True,
                "sort_order": 2,
            },
            {
                "name": "pack_100",
                "display_name": "Pack 100",
                "migrations_count": 100,
                "price_cents": 3500,
                "currency": "usd",
                "is_active": True,
                "sort_order": 3,
            },
            {
                "name": "pack_500",
                "display_name": "Pack 500",
                "migrations_count": 500,
                "price_cents": 15000,
                "currency": "usd",
                "is_active": True,
                "sort_order": 4,
            },
            {
                "name": "pack_1000",
                "display_name": "Pack 1000",
                "migrations_count": 1000,
                "price_cents": 25000,
                "currency": "usd",
                "is_active": True,
                "sort_order": 5,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("migration_packs")