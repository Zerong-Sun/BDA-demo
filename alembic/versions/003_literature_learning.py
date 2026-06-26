"""Literature documents, chunks, claims, and evidence.

Revision ID: 003_literature_learning
Revises: 002_research_catalog
Create Date: 2026-06-25
"""

from pathlib import Path

from alembic import op

revision = "003_literature_learning"
down_revision = "002_research_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "backend" / "db" / "schema.sql"
    schema = schema_path.read_text()
    start = schema.index("CREATE TABLE IF NOT EXISTS literature_documents")
    end = schema.index("CREATE TABLE IF NOT EXISTS audit_logs")
    op.execute(schema[start:end])
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_literature_documents_doi ON literature_documents(doi)",
        "CREATE INDEX IF NOT EXISTS idx_literature_documents_pmid ON literature_documents(pmid)",
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_scientific_claims_document ON scientific_claims(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_scientific_claims_review ON scientific_claims(review_status)",
        "CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim ON claim_evidence(claim_id)",
    ):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS claim_relations")
    op.execute("DROP TABLE IF EXISTS claim_evidence")
    op.execute("DROP TABLE IF EXISTS scientific_claims")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS literature_documents")
