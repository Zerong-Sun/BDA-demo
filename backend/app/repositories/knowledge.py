from __future__ import annotations

import json
import re
import sqlite3
import uuid

from .base import decode_row, decode_rows

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "of",
    "or",
    "should",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}


def list_entries(
    connection: sqlite3.Connection,
    *,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where = ["status = 'active'"]
    params: list[object] = []
    if category:
        where.append("category = ?")
        params.append(category)
    where_sql = " AND ".join(where)
    total = connection.execute(
        f"SELECT COUNT(*) AS total FROM knowledge_entries WHERE {where_sql}",
        params,
    ).fetchone()["total"]
    rows = connection.execute(
        f"""
        SELECT * FROM knowledge_entries
        WHERE {where_sql}
        ORDER BY category, title
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()
    return decode_rows(rows), int(total)


def get_entry(connection: sqlite3.Connection, knowledge_entry_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM knowledge_entries WHERE knowledge_entry_id = ? AND status = 'active'",
        (knowledge_entry_id,),
    ).fetchone()
    return decode_row(row)


def upsert_entry(connection: sqlite3.Connection, payload) -> dict:
    knowledge_entry_id = payload.knowledge_entry_id or f"kb_manual_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO knowledge_entries (
            knowledge_entry_id, title, category, subcategory, summary, content,
            tags_json, related_model_plugins, related_method_plugins, source_type,
            citation, confidence, metadata_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        ON CONFLICT(knowledge_entry_id) DO UPDATE SET
            title=excluded.title,
            category=excluded.category,
            subcategory=excluded.subcategory,
            summary=excluded.summary,
            content=excluded.content,
            tags_json=excluded.tags_json,
            related_model_plugins=excluded.related_model_plugins,
            related_method_plugins=excluded.related_method_plugins,
            source_type=excluded.source_type,
            citation=excluded.citation,
            confidence=excluded.confidence,
            metadata_json=excluded.metadata_json,
            status='active',
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            knowledge_entry_id,
            payload.title.strip(),
            payload.category.strip(),
            payload.subcategory.strip() if payload.subcategory else None,
            payload.summary.strip(),
            payload.content.strip(),
            json.dumps([tag.strip() for tag in payload.tags if tag.strip()]),
            json.dumps([item.strip() for item in payload.related_model_plugins if item.strip()]),
            json.dumps([item.strip() for item in payload.related_method_plugins if item.strip()]),
            payload.source_type.strip(),
            payload.citation.strip() if payload.citation else None,
            payload.confidence.strip(),
            json.dumps(payload.metadata),
        ),
    )
    connection.commit()
    item = get_entry(connection, knowledge_entry_id)
    if item is None:
        raise ValueError("knowledge_entry_upsert_failed")
    return item


def archive_entry(connection: sqlite3.Connection, knowledge_entry_id: str) -> dict | None:
    connection.execute(
        """
        UPDATE knowledge_entries
        SET status = 'archived', updated_at = CURRENT_TIMESTAMP
        WHERE knowledge_entry_id = ? AND status = 'active'
        """,
        (knowledge_entry_id,),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM knowledge_entries WHERE knowledge_entry_id = ?",
        (knowledge_entry_id,),
    ).fetchone()
    return decode_row(row)


def search_entries(
    connection: sqlite3.Connection,
    query: str,
    *,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", query.lower())
        if len(token) > 1 and token not in STOPWORDS
    ]
    if not tokens:
        items, _ = list_entries(connection, category=category, limit=limit)
        return items

    where = ["status = 'active'"]
    params: list[object] = []
    if category:
        where.append("category = ?")
        params.append(category)
    where_sql = " AND ".join(where)
    rows = connection.execute(
        f"""
        SELECT * FROM knowledge_entries
        WHERE {where_sql}
        """,
        params,
    ).fetchall()
    entries = decode_rows(rows)

    def score(entry: dict) -> tuple[int, str]:
        haystacks = {
            "title": str(entry.get("title", "")).lower(),
            "summary": str(entry.get("summary", "")).lower(),
            "content": str(entry.get("content", "")).lower(),
            "category": str(entry.get("category", "")).lower(),
            "tags": " ".join(entry.get("tags_json") or []).lower(),
        }
        value = 0
        for token in tokens:
            if token in haystacks["title"]:
                value += 8
            if token in haystacks["tags"]:
                value += 5
            if token in haystacks["summary"]:
                value += 3
            if token in haystacks["category"]:
                value += 2
            if token in haystacks["content"]:
                value += 1
        return value, str(entry.get("title", ""))

    ranked = sorted(entries, key=score, reverse=True)
    return [entry for entry in ranked if score(entry)[0] > 0][:limit]
