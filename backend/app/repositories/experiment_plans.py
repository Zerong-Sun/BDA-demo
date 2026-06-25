from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows


def create_plan(
    connection: sqlite3.Connection,
    *,
    experiment_plan_id: str,
    project_id: str,
    workflow_plan_id: str | None,
    workflow_run_id: str | None,
    node_run_id: str | None,
    title: str,
    objective: str,
    ethics_requirements: list[dict[str, Any]],
    regulatory_questions: list[dict[str, Any]],
    result_template: dict[str, Any],
    created_by: str,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO experiment_plans (
            experiment_plan_id, project_id, workflow_plan_id, workflow_run_id,
            node_run_id, title, objective, ethics_requirements_json,
            regulatory_questions_json, result_template_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_plan_id,
            project_id,
            workflow_plan_id,
            workflow_run_id,
            node_run_id,
            title,
            objective,
            json.dumps(ethics_requirements, ensure_ascii=False),
            json.dumps(regulatory_questions, ensure_ascii=False),
            json.dumps(result_template, ensure_ascii=False),
            created_by,
        ),
    )
    return get_plan(connection, experiment_plan_id) or {}


def replace_steps(
    connection: sqlite3.Connection,
    experiment_plan_id: str,
    steps: list[dict[str, Any]],
) -> None:
    connection.execute(
        "DELETE FROM experiment_plan_steps WHERE experiment_plan_id = ?",
        (experiment_plan_id,),
    )
    for index, step in enumerate(steps):
        connection.execute(
            """
            INSERT INTO experiment_plan_steps (
                experiment_plan_step_id, experiment_plan_id, stage_key, stage_order,
                title, purpose, samples_json, controls_json, readouts_json,
                acceptance_criteria_json, dependencies_json, owner, safety_level,
                status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step["experiment_plan_step_id"],
                experiment_plan_id,
                step["stage_key"],
                step.get("stage_order", index + 1),
                step["title"],
                step["purpose"],
                json.dumps(step.get("samples", []), ensure_ascii=False),
                json.dumps(step.get("controls", []), ensure_ascii=False),
                json.dumps(step.get("readouts", []), ensure_ascii=False),
                json.dumps(step.get("acceptance_criteria", []), ensure_ascii=False),
                json.dumps(step.get("dependencies", []), ensure_ascii=False),
                step.get("owner"),
                step.get("safety_level", "high_level_plan"),
                step.get("status", "planned"),
                step.get("notes"),
            ),
        )


def get_plan(connection: sqlite3.Connection, experiment_plan_id: str) -> dict[str, Any] | None:
    item = decode_row(connection.execute(
        "SELECT * FROM experiment_plans WHERE experiment_plan_id = ?",
        (experiment_plan_id,),
    ).fetchone())
    if item is None:
        return None
    item["steps"] = decode_rows(connection.execute(
        """
        SELECT * FROM experiment_plan_steps
        WHERE experiment_plan_id = ?
        ORDER BY stage_order, created_at
        """,
        (experiment_plan_id,),
    ).fetchall())
    return item


def get_by_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT experiment_plan_id FROM experiment_plans
        WHERE workflow_run_id = ?
        ORDER BY version DESC, created_at DESC LIMIT 1
        """,
        (workflow_run_id,),
    ).fetchone()
    return get_plan(connection, row["experiment_plan_id"]) if row else None


def update_plan(
    connection: sqlite3.Connection,
    experiment_plan_id: str,
    *,
    title: str | None = None,
    objective: str | None = None,
    status: str | None = None,
    ethics_requirements: list[dict[str, Any]] | None = None,
    regulatory_questions: list[dict[str, Any]] | None = None,
    result_template: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []
    values = {
        "title": title,
        "objective": objective,
        "status": status,
        "ethics_requirements_json": (
            json.dumps(ethics_requirements, ensure_ascii=False)
            if ethics_requirements is not None else None
        ),
        "regulatory_questions_json": (
            json.dumps(regulatory_questions, ensure_ascii=False)
            if regulatory_questions is not None else None
        ),
        "result_template_json": (
            json.dumps(result_template, ensure_ascii=False)
            if result_template is not None else None
        ),
    }
    for column, value in values.items():
        if value is not None:
            updates.append(f"{column} = ?")
            params.append(value)
    params.append(experiment_plan_id)
    connection.execute(
        f"UPDATE experiment_plans SET {', '.join(updates)} WHERE experiment_plan_id = ?",
        params,
    )
    return get_plan(connection, experiment_plan_id)


def update_step(
    connection: sqlite3.Connection,
    step_id: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {
        "title": "title",
        "purpose": "purpose",
        "samples": "samples_json",
        "controls": "controls_json",
        "readouts": "readouts_json",
        "acceptance_criteria": "acceptance_criteria_json",
        "dependencies": "dependencies_json",
        "owner": "owner",
        "status": "status",
        "notes": "notes",
        "result_artifact_id": "result_artifact_id",
    }
    json_fields = {
        "samples", "controls", "readouts", "acceptance_criteria", "dependencies",
    }
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []
    for key, column in allowed.items():
        if key not in payload:
            continue
        value = payload[key]
        if key in json_fields:
            value = json.dumps(value, ensure_ascii=False)
        updates.append(f"{column} = ?")
        params.append(value)
    params.append(step_id)
    connection.execute(
        f"UPDATE experiment_plan_steps SET {', '.join(updates)} WHERE experiment_plan_step_id = ?",
        params,
    )
    return decode_row(connection.execute(
        "SELECT * FROM experiment_plan_steps WHERE experiment_plan_step_id = ?",
        (step_id,),
    ).fetchone())


def synchronize_plan_status(
    connection: sqlite3.Connection,
    experiment_plan_id: str,
) -> dict[str, Any] | None:
    plan = get_plan(connection, experiment_plan_id)
    if plan is None:
        return None
    statuses = {step["status"] for step in plan["steps"]}
    if plan["steps"] and statuses == {"completed"}:
        status = "completed"
    elif statuses.intersection({"ready", "in_progress", "completed", "blocked"}):
        status = "active"
    else:
        status = "draft"
    if plan.get("status") != status:
        connection.execute(
            """
            UPDATE experiment_plans
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE experiment_plan_id = ?
            """,
            (status, experiment_plan_id),
        )
    return get_plan(connection, experiment_plan_id)
