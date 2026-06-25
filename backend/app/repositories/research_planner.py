from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows


def create_brief(
    connection: sqlite3.Connection,
    *,
    research_brief_id: str,
    project_id: str,
    title: str,
    objective: str,
    product_context: str,
    constraints: dict[str, Any],
    source_material: list[dict[str, Any]],
    assumptions: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO research_briefs (
            research_brief_id, project_id, title, objective, product_context,
            constraints_json, source_material_json, assumptions_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            research_brief_id,
            project_id,
            title,
            objective,
            product_context,
            json.dumps(constraints, ensure_ascii=False),
            json.dumps(source_material, ensure_ascii=False),
            json.dumps(assumptions, ensure_ascii=False),
            created_by,
        ),
    )
    return get_brief(connection, research_brief_id) or {}


def get_brief(connection: sqlite3.Connection, research_brief_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM research_briefs WHERE research_brief_id = ?",
        (research_brief_id,),
    ).fetchone()
    return decode_row(row)


def list_project_briefs(connection: sqlite3.Connection, project_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM research_briefs WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    return decode_rows(rows)


def append_source_material(
    connection: sqlite3.Connection,
    research_brief_id: str,
    source: dict[str, Any],
) -> dict[str, Any] | None:
    brief = get_brief(connection, research_brief_id)
    if brief is None:
        return None
    materials = list(brief.get("source_material_json") or [])
    source_id = source.get("source_id")
    materials = [
        item for item in materials
        if not source_id or item.get("source_id") != source_id
    ]
    materials.append(source)
    connection.execute(
        """
        UPDATE research_briefs
        SET source_material_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE research_brief_id = ?
        """,
        (json.dumps(materials, ensure_ascii=False), research_brief_id),
    )
    return get_brief(connection, research_brief_id)


def replace_findings(
    connection: sqlite3.Connection,
    research_brief_id: str,
    findings: list[dict[str, Any]],
) -> None:
    connection.execute(
        "DELETE FROM research_findings WHERE research_brief_id = ?",
        (research_brief_id,),
    )
    for finding in findings:
        connection.execute(
            """
            INSERT INTO research_findings (
                research_finding_id, research_brief_id, track, title, statement,
                evidence_level, source_refs_json, uncertainty, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding["research_finding_id"],
                research_brief_id,
                finding["track"],
                finding["title"],
                finding["statement"],
                finding.get("evidence_level", "research_seed"),
                json.dumps(finding.get("source_refs", []), ensure_ascii=False),
                finding.get("uncertainty"),
                finding.get("review_status", "pending_review"),
            ),
        )


def list_findings(connection: sqlite3.Connection, research_brief_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM research_findings
        WHERE research_brief_id = ?
        ORDER BY track, created_at, research_finding_id
        """,
        (research_brief_id,),
    ).fetchall()
    return decode_rows(rows)


def create_plan(
    connection: sqlite3.Connection,
    *,
    workflow_plan_id: str,
    research_brief_id: str,
    project_id: str,
    name: str,
    selected_route: str | None,
    route_options: list[dict[str, Any]],
    dossier: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO workflow_plans (
            workflow_plan_id, research_brief_id, project_id, name, selected_route,
            route_options_json, dossier_json, nodes_json, edges_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_plan_id,
            research_brief_id,
            project_id,
            name,
            selected_route,
            json.dumps(route_options, ensure_ascii=False),
            json.dumps(dossier, ensure_ascii=False),
            json.dumps(nodes, ensure_ascii=False),
            json.dumps(edges, ensure_ascii=False),
            created_by,
        ),
    )
    connection.execute(
        "UPDATE research_briefs SET status = 'planned', updated_at = CURRENT_TIMESTAMP WHERE research_brief_id = ?",
        (research_brief_id,),
    )
    return get_plan(connection, workflow_plan_id) or {}


def get_plan(connection: sqlite3.Connection, workflow_plan_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM workflow_plans WHERE workflow_plan_id = ?",
        (workflow_plan_id,),
    ).fetchone()
    item = decode_row(row)
    if item is None:
        return None
    item["parameter_recommendations"] = decode_rows(connection.execute(
        """
        SELECT * FROM parameter_recommendations
        WHERE workflow_plan_id = ?
        ORDER BY node_key, parameter_key
        """,
        (workflow_plan_id,),
    ).fetchall())
    item["decision_gates"] = decode_rows(connection.execute(
        """
        SELECT * FROM decision_gates
        WHERE workflow_plan_id = ?
        ORDER BY created_at
        """,
        (workflow_plan_id,),
    ).fetchall())
    return item


def set_materialized(
    connection: sqlite3.Connection,
    workflow_plan_id: str,
    workflow_run_id: str,
    selected_route: str,
) -> dict[str, Any] | None:
    connection.execute(
        """
        UPDATE workflow_plans
        SET selected_route = ?, materialized_workflow_run_id = ?,
            status = 'materialized', updated_at = CURRENT_TIMESTAMP
        WHERE workflow_plan_id = ?
        """,
        (selected_route, workflow_run_id, workflow_plan_id),
    )
    return get_plan(connection, workflow_plan_id)
