"""Research execution, experiment plans, and workflow automation.

Revision ID: 008_research_execution
Revises: 007_research_planner
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "008_research_execution"
down_revision = "007_research_planner"
branch_labels = None
depends_on = None


def _execute_statements(sql: str) -> None:
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            op.get_bind().exec_driver_sql(statement)


def upgrade() -> None:
    schema = (Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql").read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS research_questions")
    end = schema.index("CREATE TABLE IF NOT EXISTS script_assets")
    _execute_statements(schema[start:end])
    index_start = schema.index("CREATE INDEX IF NOT EXISTS idx_research_questions_brief")
    index_end = schema.index("CREATE INDEX IF NOT EXISTS idx_script_assets_model")
    _execute_statements(schema[index_start:index_end])


def downgrade() -> None:
    for table in (
        "food_matrix_profiles",
        "assay_templates",
        "regulatory_precedents",
        "receptor_regions",
        "protein_scaffolds",
        "notifications",
        "run_automation_policies",
        "experiment_plan_steps",
        "experiment_plans",
        "decision_gates",
        "parameter_recommendations",
        "design_hypotheses",
        "evidence_links",
        "research_runs",
        "research_questions",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
