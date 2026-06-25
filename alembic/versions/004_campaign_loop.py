"""Campaign-based closed-loop workflow orchestration.

Revision ID: 004_campaign_loop
Revises: 003_literature_learning
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "004_campaign_loop"
down_revision = "003_literature_learning"
branch_labels = None
depends_on = None


def _execute_statements(sql: str) -> None:
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            op.get_bind().exec_driver_sql(statement)


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql"
    schema = schema_path.read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS research_campaigns")
    end = schema.index("CREATE TABLE IF NOT EXISTS audit_logs")
    _execute_statements(schema[start:end])
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_campaigns_project ON research_campaigns(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_campaign_rounds_campaign ON campaign_rounds(campaign_id, round_number)",
        "CREATE INDEX IF NOT EXISTS idx_campaign_evaluations_round ON campaign_evaluations(campaign_round_id)",
        "CREATE INDEX IF NOT EXISTS idx_campaign_decisions_round ON campaign_decisions(campaign_round_id)",
    ):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS campaign_decisions")
    op.execute("DROP TABLE IF EXISTS campaign_evaluations")
    op.execute("DROP TABLE IF EXISTS campaign_rounds")
    op.execute("DROP TABLE IF EXISTS research_campaigns")
