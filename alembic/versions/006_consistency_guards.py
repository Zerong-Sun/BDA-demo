"""Concurrency and consistency guards.

Revision ID: 006_consistency_guards
Revises: 005_literature_subscriptions
Create Date: 2026-06-25
"""

from alembic import op
from sqlalchemy import inspect

revision = "006_consistency_guards"
down_revision = "005_literature_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("claim_relations")
    }
    if "reviewed_by" not in columns:
        op.execute("ALTER TABLE claim_relations ADD COLUMN reviewed_by TEXT")
    if "reviewed_at" not in columns:
        op.execute("ALTER TABLE claim_relations ADD COLUMN reviewed_at TEXT")
    op.execute(
        """
        DELETE FROM campaign_evaluations
        WHERE evaluation_id IN (
            SELECT evaluation_id FROM (
                SELECT evaluation_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY campaign_round_id
                           ORDER BY created_at, evaluation_id
                       ) AS duplicate_rank
                FROM campaign_evaluations
            ) ranked
            WHERE duplicate_rank > 1
        )
        """
    )
    op.execute(
        """
        DELETE FROM campaign_decisions
        WHERE decision_id IN (
            SELECT decision_id FROM (
                SELECT decision_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY campaign_round_id
                           ORDER BY created_at, decision_id
                       ) AS duplicate_rank
                FROM campaign_decisions
            ) ranked
            WHERE duplicate_rank > 1
        )
        """
    )
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
