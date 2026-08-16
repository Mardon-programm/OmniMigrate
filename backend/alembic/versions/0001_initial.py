"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = sa.Enum("admin", "client", "engineer", name="user_role")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            user_role,
            nullable=False,
            server_default="client",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("repo_url", sa.String(512), nullable=True),
        sa.Column(
            "source_language", sa.String(64), nullable=False, server_default="python"
        ),
        sa.Column(
            "target_stack", sa.String(64), nullable=False, server_default="python-3.12"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "migration_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("context_rule", sa.Text(), nullable=False, server_default=""),
        sa.Column("input_code", sa.Text(), nullable=False),
        sa.Column("output_code", sa.Text(), nullable=True),
        sa.Column("diff", sa.Text(), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("self_heal_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_migration_jobs_id", "migration_jobs", ["id"])
    op.create_index("ix_migration_jobs_project_id", "migration_jobs", ["project_id"])
    op.create_index("ix_migration_jobs_status", "migration_jobs", ["status"])

    op.execute("ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email)")


def downgrade() -> None:
    op.drop_table("migration_jobs")
    op.drop_table("projects")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
