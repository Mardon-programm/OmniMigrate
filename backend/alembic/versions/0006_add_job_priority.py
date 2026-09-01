"""Add job priority column.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "migration_jobs",
        sa.Column(
            "priority",
            sa.String(length=16),
            nullable=False,
            server_default="normal",
        ),
    )
    op.create_index("ix_migration_jobs_priority", "migration_jobs", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_migration_jobs_priority", table_name="migration_jobs")
    op.drop_column("migration_jobs", "priority")
