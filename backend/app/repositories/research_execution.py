from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows


def replace_questions(
    connection: sqlite3.Connection,
    research_brief_id: str,
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    connection.execute(
        "DELETE FROM research_questions WHERE research_brief_id = ?",
        (research_brief_id,),
    )
    for item in questions:
        connection.execute(
            """
            INSERT INTO research_questions (
                research_question_id, research_brief_id, track, question,
                query_json, priority, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["research_question_id"],
                research_brief_id,
                item["track"],
                item["question"],
                json.dumps(item.get("query", {}), ensure_ascii=False),
                item.get("priority", 100),
                item.get("status", "pending"),
            ),
        )
    return list_questions(connection, research_brief_id)


def list_questions(connection: sqlite3.Connection, research_brief_id: str) -> list[dict[str, Any]]:
    return decode_rows(connection.execute(
        """
        SELECT * FROM research_questions
        WHERE research_brief_id = ?
        ORDER BY priority, created_at, research_question_id
        """,
        (research_brief_id,),
    ).fetchall())


def create_run(
    connection: sqlite3.Connection,
    *,
    research_run_id: str,
    research_brief_id: str,
    created_by: str,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO research_runs (
            research_run_id, research_brief_id, status, progress_json,
            result_summary_json, created_by
        ) VALUES (?, ?, 'draft', '{}', '{}', ?)
        """,
        (research_run_id, research_brief_id, created_by),
    )
    return get_run(connection, research_run_id) or {}


def update_run(
    connection: sqlite3.Connection,
    research_run_id: str,
    *,
    status: str,
    progress: dict[str, Any] | None = None,
    result_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = [status]
    if progress is not None:
        updates.append("progress_json = ?")
        params.append(json.dumps(progress, ensure_ascii=False))
    if result_summary is not None:
        updates.append("result_summary_json = ?")
        params.append(json.dumps(result_summary, ensure_ascii=False))
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if status == "running":
        updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
    if status in {"completed", "partial", "failed"}:
        updates.append("completed_at = CURRENT_TIMESTAMP")
    params.append(research_run_id)
    connection.execute(
        f"UPDATE research_runs SET {', '.join(updates)} WHERE research_run_id = ?",
        params,
    )
    return get_run(connection, research_run_id)


def get_run(connection: sqlite3.Connection, research_run_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM research_runs WHERE research_run_id = ?",
        (research_run_id,),
    ).fetchone()
    item = decode_row(row)
    if item is None:
        return None
    item["questions"] = list_questions(connection, item["research_brief_id"])
    item["evidence"] = list_evidence(connection, research_run_id)
    return item


def list_runs(connection: sqlite3.Connection, research_brief_id: str) -> list[dict[str, Any]]:
    return decode_rows(connection.execute(
        "SELECT * FROM research_runs WHERE research_brief_id = ? ORDER BY created_at DESC",
        (research_brief_id,),
    ).fetchall())


def replace_evidence(
    connection: sqlite3.Connection,
    research_run_id: str,
    evidence: list[dict[str, Any]],
) -> None:
    connection.execute("DELETE FROM evidence_links WHERE research_run_id = ?", (research_run_id,))
    for item in evidence:
        connection.execute(
            """
            INSERT INTO evidence_links (
                evidence_link_id, research_run_id, research_question_id,
                research_finding_id, source_type, source_identifier, title,
                uri, evidence_excerpt, evidence_level, applicability_json,
                metadata_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["evidence_link_id"],
                research_run_id,
                item.get("research_question_id"),
                item.get("research_finding_id"),
                item["source_type"],
                item.get("source_identifier"),
                item["title"],
                item.get("uri"),
                item.get("evidence_excerpt"),
                item.get("evidence_level", "metadata"),
                json.dumps(item.get("applicability", {}), ensure_ascii=False),
                json.dumps(item.get("metadata", {}), ensure_ascii=False),
                item.get("review_status", "pending_review"),
            ),
        )


def list_evidence(connection: sqlite3.Connection, research_run_id: str) -> list[dict[str, Any]]:
    return decode_rows(connection.execute(
        """
        SELECT * FROM evidence_links
        WHERE research_run_id = ?
        ORDER BY source_type, created_at, evidence_link_id
        """,
        (research_run_id,),
    ).fetchall())


def review_evidence(
    connection: sqlite3.Connection,
    evidence_link_id: str,
    review_status: str,
    reviewed_by: str,
) -> dict[str, Any] | None:
    connection.execute(
        """
        UPDATE evidence_links
        SET review_status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE evidence_link_id = ?
        """,
        (review_status, reviewed_by, evidence_link_id),
    )
    return decode_row(connection.execute(
        "SELECT * FROM evidence_links WHERE evidence_link_id = ?",
        (evidence_link_id,),
    ).fetchone())


def replace_hypotheses(
    connection: sqlite3.Connection,
    research_brief_id: str,
    hypotheses: list[dict[str, Any]],
) -> None:
    connection.execute(
        "DELETE FROM design_hypotheses WHERE research_brief_id = ?",
        (research_brief_id,),
    )
    for item in hypotheses:
        connection.execute(
            """
            INSERT INTO design_hypotheses (
                design_hypothesis_id, research_brief_id, hypothesis, rationale,
                falsification_test, evidence_link_ids_json, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["design_hypothesis_id"],
                research_brief_id,
                item["hypothesis"],
                item.get("rationale"),
                item.get("falsification_test"),
                json.dumps(item.get("evidence_link_ids", [])),
                item.get("confidence", "low"),
                item.get("status", "proposed"),
            ),
        )


def list_hypotheses(connection: sqlite3.Connection, research_brief_id: str) -> list[dict[str, Any]]:
    return decode_rows(connection.execute(
        "SELECT * FROM design_hypotheses WHERE research_brief_id = ? ORDER BY created_at",
        (research_brief_id,),
    ).fetchall())
