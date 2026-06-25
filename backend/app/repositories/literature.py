from __future__ import annotations

import re
import sqlite3
from typing import Any

from .base import decode_row, decode_rows

STOPWORDS = {
    "a", "an", "and", "are", "for", "from", "in", "of", "on", "or",
    "the", "to", "was", "were", "with",
}


def get_document(connection: sqlite3.Connection, document_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM literature_documents WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    document = decode_row(row)
    if document is None:
        return None
    chunks = connection.execute(
        "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index",
        (document_id,),
    ).fetchall()
    claims = connection.execute(
        """
        SELECT c.*, e.evidence_id, e.chunk_id, e.evidence_excerpt,
               e.start_offset, e.end_offset, e.evidence_role
        FROM scientific_claims c
        LEFT JOIN claim_evidence e ON e.claim_id = c.claim_id
        WHERE c.document_id = ?
        ORDER BY c.created_at, e.created_at
        """,
        (document_id,),
    ).fetchall()
    document["chunks"] = decode_rows(chunks)
    document["claims"] = decode_rows(claims)
    return document


def search_library(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    accepted_only: bool = False,
) -> list[dict[str, Any]]:
    tokens = [
        token for token in re.findall(r"[A-Za-z0-9_.-]+", query.lower())
        if len(token) > 1 and token not in STOPWORDS
    ]
    claim_filter = "AND c.review_status = 'accepted'" if accepted_only else ""
    search_filter = ""
    params: list[Any] = []
    if tokens:
        clauses = []
        for token in tokens:
            pattern = f"%{token}%"
            clauses.append(
                "(LOWER(d.title) LIKE ? OR LOWER(COALESCE(d.abstract_text, '')) LIKE ? "
                "OR LOWER(COALESCE(c.statement, '')) LIKE ? "
                "OR LOWER(COALESCE(e.evidence_excerpt, '')) LIKE ? "
                "OR EXISTS ("
                "SELECT 1 FROM document_chunks dc "
                "WHERE dc.document_id = d.document_id AND LOWER(dc.content) LIKE ?"
                "))"
            )
            params.extend([pattern, pattern, pattern, pattern, pattern])
        search_filter = "AND (" + " OR ".join(clauses) + ")"
    rows = connection.execute(
        f"""
        SELECT d.document_id, d.title, d.authors, d.journal, d.publication_year,
               d.doi, d.pmid, d.pmcid, d.abstract_text, d.content_kind,
               d.full_text_status, d.metadata_json, d.external_source, d.external_id,
               c.claim_id, c.statement, c.claim_type, c.context_json,
               c.confidence, c.review_status, c.extraction_method,
               e.chunk_id, e.evidence_excerpt, e.evidence_role,
               ch.section_title, ch.section_path,
               COALESCE((
                   SELECT GROUP_CONCAT(dc2.content, ' ')
                   FROM document_chunks dc2
                   WHERE dc2.document_id = d.document_id
               ), '') AS document_chunk_text
        FROM literature_documents d
        LEFT JOIN scientific_claims c ON c.document_id = d.document_id {claim_filter}
        LEFT JOIN claim_evidence e ON e.claim_id = c.claim_id
        LEFT JOIN document_chunks ch ON ch.chunk_id = e.chunk_id
        WHERE d.status = 'active' {search_filter}
        LIMIT 500
        """,
        params,
    ).fetchall()
    items = decode_rows(rows)

    def score(item: dict[str, Any]) -> tuple[int, int]:
        title = str(item.get("title") or "").lower()
        statement = str(item.get("statement") or "").lower()
        evidence = str(item.get("evidence_excerpt") or "").lower()
        abstract = str(item.get("abstract_text") or "").lower()
        chunk_text = str(item.get("document_chunk_text") or "").lower()
        value = 0
        for token in tokens:
            value += 8 if token in title else 0
            value += 6 if token in statement else 0
            value += 3 if token in evidence else 0
            value += 1 if token in abstract else 0
            value += 2 if token in chunk_text else 0
        return value, int(item.get("publication_year") or 0)

    ranked = sorted(items, key=score, reverse=True)
    if tokens:
        ranked = [item for item in ranked if score(item)[0] > 0]
    return ranked[:max(1, min(limit, 50))]


def list_claims(
    connection: sqlite3.Connection,
    *,
    review_status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if review_status:
        where = "WHERE c.review_status = ?"
        params.append(review_status)
    rows = connection.execute(
        f"""
        SELECT c.*, d.title, d.doi, d.pmid, d.pmcid,
               e.chunk_id, e.evidence_excerpt, e.evidence_role
        FROM scientific_claims c
        JOIN literature_documents d ON d.document_id = c.document_id
        LEFT JOIN claim_evidence e ON e.claim_id = c.claim_id
        {where}
        ORDER BY c.created_at DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return decode_rows(rows)


def review_claim(
    connection: sqlite3.Connection,
    claim_id: str,
    *,
    review_status: str,
    reviewed_by: str,
) -> dict | None:
    connection.execute(
        """
        UPDATE scientific_claims
        SET review_status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE claim_id = ?
        """,
        (review_status, reviewed_by, claim_id),
    )
    row = connection.execute(
        "SELECT * FROM scientific_claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    return decode_row(row)


def list_relations(
    connection: sqlite3.Connection,
    *,
    review_status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if review_status:
        where = "WHERE r.review_status = ?"
        params.append(review_status)
    rows = connection.execute(
        f"""
        SELECT r.*, source.statement AS source_statement,
               target.statement AS target_statement,
               source_doc.title AS source_title,
               target_doc.title AS target_title
        FROM claim_relations r
        JOIN scientific_claims source ON source.claim_id = r.source_claim_id
        JOIN scientific_claims target ON target.claim_id = r.target_claim_id
        JOIN literature_documents source_doc ON source_doc.document_id = source.document_id
        JOIN literature_documents target_doc ON target_doc.document_id = target.document_id
        {where}
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return decode_rows(rows)


def review_relation(
    connection: sqlite3.Connection,
    relation_id: str,
    *,
    review_status: str,
    reviewed_by: str,
) -> dict | None:
    connection.execute(
        """
        UPDATE claim_relations
        SET review_status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE relation_id = ?
        """,
        (review_status, reviewed_by, relation_id),
    )
    row = connection.execute(
        "SELECT * FROM claim_relations WHERE relation_id = ?",
        (relation_id,),
    ).fetchone()
    return decode_row(row)
