from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import decode_row, decode_rows


def list_subscriptions(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM literature_subscriptions ORDER BY created_at DESC"
    ).fetchall()
    return decode_rows(rows)


def get_subscription(connection: sqlite3.Connection, subscription_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM literature_subscriptions WHERE subscription_id = ?",
        (subscription_id,),
    ).fetchone()
    return decode_row(row)


def due_subscriptions(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT * FROM literature_subscriptions
        WHERE enabled = 1 AND next_run_at <= CURRENT_TIMESTAMP
        ORDER BY next_run_at
        """
    ).fetchall()
    return decode_rows(rows)


def claim_due_subscription(
    connection: sqlite3.Connection,
    subscription_id: str,
) -> dict | None:
    # Move next_run_at forward before doing network/LLM work so concurrent Beat
    # workers cannot claim the same subscription. A failed run is still retried
    # on the normal interval and records its failure status.
    item = get_subscription(connection, subscription_id)
    if item is None:
        return None
    next_run = datetime.now(timezone.utc) + timedelta(hours=int(item["interval_hours"]))
    cursor = connection.execute(
        """
        UPDATE literature_subscriptions
        SET next_run_at=?, last_status='running', updated_at=CURRENT_TIMESTAMP
        WHERE subscription_id=? AND enabled=1 AND next_run_at <= CURRENT_TIMESTAMP
        """,
        (next_run.isoformat(), subscription_id),
    )
    if cursor.rowcount != 1:
        return None
    return get_subscription(connection, subscription_id)


def record_run(
    connection: sqlite3.Connection,
    subscription_id: str,
    *,
    status: str,
    result: dict[str, Any],
) -> None:
    item = get_subscription(connection, subscription_id)
    if item is None:
        return
    next_run = datetime.now(timezone.utc) + timedelta(hours=int(item["interval_hours"]))
    connection.execute(
        """
        UPDATE literature_subscriptions
        SET last_run_at=CURRENT_TIMESTAMP,
            next_run_at=CASE WHEN last_status='running' THEN next_run_at ELSE ? END,
            last_status=?,
            last_result_json=?, updated_at=CURRENT_TIMESTAMP
        WHERE subscription_id=?
        """,
        (next_run.isoformat(), status, json.dumps(result), subscription_id),
    )
