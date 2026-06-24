"""Research sources, script assets, and model parameter catalog.

Revision ID: 002_research_catalog
Revises: 001_extended
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "002_research_catalog"
down_revision = "001_extended"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql"
    schema = schema_path.read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS research_sources")
    end = schema.index("CREATE TABLE IF NOT EXISTS audit_logs")
    op.execute(schema[start:end])
    op.execute("CREATE INDEX IF NOT EXISTS idx_research_sources_type ON research_sources(source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_script_assets_model ON script_assets(model_plugin_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parameter_catalog_model ON model_parameter_catalog(model_plugin_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_script_parameter_model ON script_parameter_observations(model_plugin_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS script_parameter_observations")
    op.execute("DROP TABLE IF EXISTS model_parameter_catalog")
    op.execute("DROP TABLE IF EXISTS script_assets")
    op.execute("DROP TABLE IF EXISTS research_sources")
