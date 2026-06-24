"""Concurrency and consistency guards.

Revision ID: 006_consistency_guards
Revises: 005_literature_subscriptions
Create Date: 2026-06-25
"""

from alembic import op

revision = "006_consistency_guards"
down_revision = "005_literature_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_evaluation_round "
        "ON campaign_evaluations(campaign_round_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_decision_round "
        "ON campaign_decisions(campaign_round_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_campaign_decision_round")
    op.execute("DROP INDEX IF EXISTS uq_campaign_evaluation_round")
