"""Scheduled literature subscriptions.

Revision ID: 005_literature_subscriptions
Revises: 004_campaign_loop
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "005_literature_subscriptions"
down_revision = "004_campaign_loop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql"
    schema = schema_path.read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS literature_subscriptions")
    end = schema.index("CREATE TABLE IF NOT EXISTS audit_logs")
    op.execute(schema[start:end])
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_literature_subscriptions_due "
        "ON literature_subscriptions(enabled, next_run_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS literature_subscriptions")
