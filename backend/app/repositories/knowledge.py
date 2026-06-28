from __future__ import annotations

import re
import sqlite3

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
