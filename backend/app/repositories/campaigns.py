from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows


def get_campaign(connection: sqlite3.Connection, campaign_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM research_campaigns WHERE campaign_id = ?",
        (campaign_id,),
    ).fetchone()
    return decode_row(row)


def list_project_campaigns(connection: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT * FROM research_campaigns
        WHERE project_id = ?
        ORDER BY created_at DESC
        """,
        (project_id,),
    ).fetchall()
    return decode_rows(rows)


def get_round(connection: sqlite3.Connection, campaign_round_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM campaign_rounds WHERE campaign_round_id = ?",
        (campaign_round_id,),
    ).fetchone()
    return decode_row(row)


def get_round_by_number(
    connection: sqlite3.Connection,
    campaign_id: str,
    round_number: int,
) -> dict | None:
    row = connection.execute(
        """
        SELECT * FROM campaign_rounds
        WHERE campaign_id = ? AND round_number = ?
        """,
        (campaign_id, round_number),
    ).fetchone()
    return decode_row(row)


def list_rounds(connection: sqlite3.Connection, campaign_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT * FROM campaign_rounds
        WHERE campaign_id = ?
        ORDER BY round_number
        """,
        (campaign_id,),
    ).fetchall()
    return decode_rows(rows)


def get_campaign_detail(connection: sqlite3.Connection, campaign_id: str) -> dict | None:
    campaign = get_campaign(connection, campaign_id)
    if campaign is None:
        return None
    rounds = list_rounds(connection, campaign_id)
    for item in rounds:
        item["evaluations"] = decode_rows(connection.execute(
            """
            SELECT * FROM campaign_evaluations
            WHERE campaign_round_id = ?
            ORDER BY created_at DESC
            """,
            (item["campaign_round_id"],),
        ).fetchall())
        item["decisions"] = decode_rows(connection.execute(
            """
            SELECT * FROM campaign_decisions
            WHERE campaign_round_id = ?
            ORDER BY created_at DESC
            """,
            (item["campaign_round_id"],),
        ).fetchall())
    campaign["rounds"] = rounds
    return campaign


def create_campaign(
    connection: sqlite3.Connection,
    *,
    campaign_id: str,
    project_id: str,
    name: str,
    objective: str,
    max_rounds: int,
    budget: dict[str, Any],
    stop_conditions: list[dict[str, Any]],
    strategy: dict[str, Any],
    created_by: str,
) -> dict:
    connection.execute(
        """
        INSERT INTO research_campaigns (
            campaign_id, project_id, name, objective, status, max_rounds,
            current_round, budget_json, stop_conditions_json, strategy_json,
            created_by
        ) VALUES (?, ?, ?, ?, 'active', ?, 1, ?, ?, ?, ?)
        """,
        (
            campaign_id,
            project_id,
            name,
            objective,
            max_rounds,
            json.dumps(budget),
            json.dumps(stop_conditions),
            json.dumps(strategy),
            created_by,
        ),
    )
    return get_campaign(connection, campaign_id) or {}


def update_campaign_status(
    connection: sqlite3.Connection,
    campaign_id: str,
    *,
    status: str,
    current_round: int | None = None,
) -> dict | None:
    if current_round is None:
        connection.execute(
            """
            UPDATE research_campaigns
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE campaign_id = ?
            """,
            (status, campaign_id),
        )
    else:
        connection.execute(
            """
            UPDATE research_campaigns
            SET status = ?, current_round = ?, updated_at = CURRENT_TIMESTAMP
            WHERE campaign_id = ?
            """,
            (status, current_round, campaign_id),
        )
    return get_campaign(connection, campaign_id)


def get_decision(connection: sqlite3.Connection, decision_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM campaign_decisions WHERE decision_id = ?",
        (decision_id,),
    ).fetchone()
    return decode_row(row)
