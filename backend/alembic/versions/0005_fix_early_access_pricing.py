"""Fix: Early Access plans pricing

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update plan names and pricing to match Early Access
    op.execute("""
        UPDATE plans SET
            name = 'Starter',
            amount_cents = 1900,
            max_jobs_per_month = 50,
            max_files_per_job = 50,
            max_llm_tokens_per_month = 1000000,
            max_org_members = 5,
            features = '{"support": "community", "migrations_per_month": 50}',
            is_active = true
        WHERE name = 'Free';
    """)

    op.execute("""
        UPDATE plans SET
            name = 'Pro',
            amount_cents = 7900,
            max_jobs_per_month = -1,
            max_files_per_job = 500,
            max_llm_tokens_per_month = 10000000,
            max_org_members = 25,
            features = '{"support": "priority", "git_integration": true, "migrations_per_month": "unlimited"}',
            is_active = true
        WHERE name = 'Team';
    """)

    op.execute("""
        UPDATE plans SET
            name = 'Enterprise',
            amount_cents = 0,
            max_jobs_per_month = -1,
            max_files_per_job = -1,
            max_llm_tokens_per_month = -1,
            max_org_members = -1,
            features = '{"support": "dedicated", "git_integration": true, "sla": true, "custom_pricing": true}',
            is_active = true
        WHERE name = 'Enterprise';
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE plans SET
            name = 'Free',
            amount_cents = 0,
            max_jobs_per_month = 10,
            max_files_per_job = 50,
            max_llm_tokens_per_month = 100000,
            max_org_members = 5,
            features = '{"support": "community"}',
            is_active = true
        WHERE name = 'Starter';
    """)

    op.execute("""
        UPDATE plans SET
            name = 'Team',
            amount_cents = 4900,
            max_jobs_per_month = 100,
            max_files_per_job = 500,
            max_llm_tokens_per_month = 2000000,
            max_org_members = 25,
            features = '{"support": "priority", "git_integration": true}',
            is_active = true
        WHERE name = 'Pro';
    """)

    op.execute("""
        UPDATE plans SET
            name = 'Enterprise',
            amount_cents = 19900,
            max_jobs_per_month = 2147483647,
            max_files_per_job = 2147483647,
            max_llm_tokens_per_month = 2147483647,
            max_org_members = 2147483647,
            features = '{"support": "dedicated", "git_integration": true, "sla": true}',
            is_active = true
        WHERE name = 'Enterprise';
    """)