"""Research briefs and evidence-driven workflow plans.

Revision ID: 007_research_planner
Revises: 006_consistency_guards
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "007_research_planner"
down_revision = "006_consistency_guards"
branch_labels = None
depends_on = None


def _execute_statements(sql: str) -> None:
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            op.get_bind().exec_driver_sql(statement)


def upgrade() -> None:
    schema = (Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql").read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS research_briefs")
    end = schema.index("CREATE TABLE IF NOT EXISTS research_questions")
    _execute_statements(schema[start:end])
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_research_briefs_project ON research_briefs(project_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_research_findings_brief ON research_findings(research_brief_id, track)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_plans_brief ON workflow_plans(research_brief_id, created_at)",
    ):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow_plans")
    op.execute("DROP TABLE IF EXISTS research_findings")
    op.execute("DROP TABLE IF EXISTS research_briefs")
