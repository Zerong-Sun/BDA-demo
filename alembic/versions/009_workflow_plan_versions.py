"""Version workflow plans for reproducible research exports.

Revision ID: 009_workflow_plan_versions
Revises: 008_research_execution
Create Date: 2026-06-25
"""

import sqlalchemy as sa
from alembic import op

revision = "009_workflow_plan_versions"
down_revision = "008_research_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("workflow_plans")
    }
    if "version" not in columns:
        op.add_column(
            "workflow_plans",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )
    if "supersedes_workflow_plan_id" not in columns:
        op.add_column(
            "workflow_plans",
            sa.Column("supersedes_workflow_plan_id", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("workflow_plans")
    }
    if "supersedes_workflow_plan_id" in columns:
        op.drop_column("workflow_plans", "supersedes_workflow_plan_id")
    if "version" in columns:
        op.drop_column("workflow_plans", "version")
