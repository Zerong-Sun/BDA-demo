"""Initial extended schema

Revision ID: 001_extended
Revises:
Create Date: 2026-06-07
"""

from pathlib import Path

from alembic import op

revision = "001_extended"
down_revision = None
branch_labels = None
depends_on = None


def _execute_statements(sql: str) -> None:
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("-- Add organization_id"):
            op.get_bind().exec_driver_sql(statement)


def upgrade() -> None:
    schema_root = Path(__file__).resolve().parents[2] / "backend" / "db"
    for filename in ("schema.sql", "schema_extended.sql"):
        schema_path = schema_root / filename
        if schema_path.exists():
            _execute_statements(schema_path.read_text())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_members")
    op.execute("DROP TABLE IF EXISTS organization_members")
    op.execute("DROP TABLE IF EXISTS organizations")
    op.execute("DROP TABLE IF EXISTS user_sessions")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS job_events")
    op.execute("DROP TABLE IF EXISTS jobs")
