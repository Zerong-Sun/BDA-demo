from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from .base import decode_row, decode_rows


def get_policy(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, Any] | None:
    return decode_row(connection.execute(
        "SELECT * FROM run_automation_policies WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchone())


def upsert_policy(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    mode: str,
    auto_submit_ready: bool,
    notify_on_ready: bool,
    notify_on_terminal: bool,
    max_auto_retries: int,
    retry_backoff_seconds: int,
    created_by: str,
) -> dict[str, Any]:
    existing = get_policy(connection, workflow_run_id)
    policy_id = (existing or {}).get("automation_policy_id") or f"policy_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO run_automation_policies (
            automation_policy_id, workflow_run_id, mode, auto_submit_ready,
            notify_on_ready, notify_on_terminal, max_auto_retries,
            retry_backoff_seconds, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow_run_id) DO UPDATE SET
            mode=excluded.mode,
            auto_submit_ready=excluded.auto_submit_ready,
            notify_on_ready=excluded.notify_on_ready,
            notify_on_terminal=excluded.notify_on_terminal,
            max_auto_retries=excluded.max_auto_retries,
            retry_backoff_seconds=excluded.retry_backoff_seconds,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            policy_id,
            workflow_run_id,
            mode,
            int(auto_submit_ready),
            int(notify_on_ready),
            int(notify_on_terminal),
            max_auto_retries,
            retry_backoff_seconds,
            created_by,
        ),
    )
    return get_policy(connection, workflow_run_id) or {}


def create_notification(
    connection: sqlite3.Connection,
    *,
    user_id: str | None,
    project_id: str | None,
    workflow_run_id: str | None,
    node_run_id: str | None,
    notification_type: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    dedupe_unread: bool = False,
) -> dict[str, Any]:
    if dedupe_unread:
        existing = decode_row(connection.execute(
            """
            SELECT * FROM notifications
            WHERE COALESCE(user_id, '') = COALESCE(?, '')
              AND COALESCE(workflow_run_id, '') = COALESCE(?, '')
              AND COALESCE(node_run_id, '') = COALESCE(?, '')
              AND notification_type = ?
              AND status = 'unread'
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, workflow_run_id, node_run_id, notification_type),
        ).fetchone())
        if existing:
            return existing
    notification_id = f"notification_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO notifications (
            notification_id, user_id, project_id, workflow_run_id, node_run_id,
            notification_type, title, message, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notification_id,
            user_id,
            project_id,
            workflow_run_id,
            node_run_id,
            notification_type,
            title,
            message,
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )
    return decode_row(connection.execute(
        "SELECT * FROM notifications WHERE notification_id = ?",
        (notification_id,),
    ).fetchone()) or {}


def list_notifications(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    project_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    clauses = ["(user_id = ? OR user_id IS NULL)"]
    params: list[Any] = [user_id]
    if project_id:
        clauses.append("project_id = ?")
        params.append(project_id)
    if unread_only:
        clauses.append("status = 'unread'")
    params.append(max(1, min(limit, 100)))
    return decode_rows(connection.execute(
        f"""
        SELECT * FROM notifications
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC LIMIT ?
        """,
        params,
    ).fetchall())


def mark_read(
    connection: sqlite3.Connection,
    notification_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    connection.execute(
        """
        UPDATE notifications SET status='read', read_at=CURRENT_TIMESTAMP
        WHERE notification_id = ? AND user_id = ?
        """,
        (notification_id, user_id),
    )
    return decode_row(connection.execute(
        "SELECT * FROM notifications WHERE notification_id = ? AND user_id = ?",
        (notification_id, user_id),
    ).fetchone())
