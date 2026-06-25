import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .base import decode_row, decode_rows, get_by_id, list_table

KD_VALUE_RE = re.compile(r"([\d.]+)")


def list_projects(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "projects", "created_at DESC")


def list_projects_paginated(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    count_row = connection.execute("SELECT COUNT(*) AS total FROM projects").fetchone()
    total = int(count_row["total"]) if count_row else 0
    rows = connection.execute(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return decode_rows(rows), total


def get_project(connection: sqlite3.Connection, project_id: str) -> dict | None:
    return get_by_id(connection, "projects", "project_id", project_id)


def create_project(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    project_name: str,
    project_type: str,
    owner_id: str | None,
    organization_id: str | None = None,
    summary: str | None = None,
) -> dict:
    connection.execute(
        """
        INSERT INTO projects (
            project_id, project_name, project_type, status, owner_id, organization_id, summary
        ) VALUES (?, ?, ?, 'draft', ?, ?, ?)
        """,
        (project_id, project_name, project_type, owner_id, organization_id, summary),
    )
    if owner_id:
        connection.execute(
            """
            INSERT OR IGNORE INTO project_members (project_id, user_id, role)
            VALUES (?, ?, 'owner')
            """,
            (project_id, owner_id),
        )
    return get_project(connection, project_id) or {}


def list_project_candidates(connection: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM candidates WHERE project_id = ? ORDER BY interface_score DESC, plddt DESC",
        (project_id,),
    ).fetchall()
    return decode_rows(rows)


def list_project_candidates_filtered(
    connection: sqlite3.Connection,
    project_id: str,
    *,
    sort: str = "interface_score",
    order: str = "desc",
    status: str | None = None,
    decision: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    sort_columns = {
        "interface_score": "interface_score",
        "plddt": "plddt",
        "pred_kd": "pred_kd",
    }
    if sort not in sort_columns:
        raise ValueError(f"invalid_sort:{sort}")
    if order.lower() not in ("asc", "desc"):
        raise ValueError(f"invalid_order:{order}")
    sort_column = sort_columns[sort]
    sort_direction = "ASC" if order.lower() == "asc" else "DESC"

    clauses = ["project_id = ?"]
    params: list[object] = [project_id]

    if status:
        clauses.append("status = ?")
        params.append(status)

    if decision:
        decisions = [item.strip() for item in decision.split(",") if item.strip()]
        if decisions:
            placeholders = ", ".join("?" for _ in decisions)
            clauses.append(f"decision IN ({placeholders})")
            params.extend(decisions)

    if search:
        clauses.append("(candidate_id LIKE ? OR family LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    where_sql = " AND ".join(clauses)
    count_row = connection.execute(
        f"SELECT COUNT(*) AS total FROM candidates WHERE {where_sql}",
        params,
    ).fetchone()
    total = int(count_row["total"]) if count_row else 0

    rows = connection.execute(
        f"""
        SELECT * FROM candidates
        WHERE {where_sql}
        ORDER BY {sort_column} {sort_direction}, plddt DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()
    return decode_rows(rows), total


def get_candidate(connection: sqlite3.Connection, candidate_id: str) -> dict | None:
    return get_by_id(connection, "candidates", "candidate_id", candidate_id)


def list_project_experiment_results(connection: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT er.*
        FROM experiment_results er
        JOIN candidates c ON c.candidate_id = er.candidate_id
        WHERE c.project_id = ?
        ORDER BY er.experiment_type, er.candidate_id
        """,
        (project_id,),
    ).fetchall()
    return decode_rows(rows)


def get_workflow_run(connection: sqlite3.Connection, workflow_run_id: str) -> dict | None:
    return get_by_id(connection, "workflow_runs", "workflow_run_id", workflow_run_id)


def get_workflow_run_project_id(connection: sqlite3.Connection, workflow_run_id: str) -> str | None:
    row = connection.execute(
        """
        SELECT dt.project_id
        FROM workflow_runs wr
        JOIN design_tasks dt ON dt.task_id = wr.task_id
        WHERE wr.workflow_run_id = ?
        LIMIT 1
        """,
        (workflow_run_id,),
    ).fetchone()
    return row["project_id"] if row else None


def get_workflow_node(connection: sqlite3.Connection, node_run_id: str) -> dict | None:
    return get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)


def list_workflow_nodes(connection: sqlite3.Connection, workflow_run_id: str) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM workflow_node_runs WHERE workflow_run_id = ? ORDER BY rowid",
        (workflow_run_id,),
    ).fetchall()
    return decode_rows(rows)


def list_workflow_edges(connection: sqlite3.Connection, workflow_run_id: str) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM workflow_edges WHERE workflow_run_id = ? ORDER BY created_at, rowid",
        (workflow_run_id,),
    ).fetchall()
    return decode_rows(rows)


def replace_workflow_edges(connection: sqlite3.Connection, workflow_run_id: str, edges: list[dict]) -> list[dict]:
    import uuid

    connection.execute("DELETE FROM workflow_edges WHERE workflow_run_id = ?", (workflow_run_id,))
    node_ids = {
        row["node_run_id"]
        for row in connection.execute(
            "SELECT node_run_id FROM workflow_node_runs WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchall()
    }
    for edge in edges:
        source = edge.get("source_node_run_id") or edge.get("source")
        target = edge.get("target_node_run_id") or edge.get("target")
        if source not in node_ids or target not in node_ids:
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO workflow_edges (
                edge_id, workflow_run_id, source_node_run_id, source_port,
                target_node_run_id, target_port, edge_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge.get("edge_id") or f"edge_{uuid.uuid4().hex[:12]}",
                workflow_run_id,
                source,
                edge.get("source_port") or edge.get("sourceHandle") or "output",
                target,
                edge.get("target_port") or edge.get("targetHandle") or "input",
                edge.get("edge_type") or edge.get("type") or "data",
                json.dumps(edge.get("metadata_json") or edge.get("data") or {}),
            ),
        )
    return list_workflow_edges(connection, workflow_run_id)


def list_workflow_nodes_paginated(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    count_row = connection.execute(
        "SELECT COUNT(*) AS total FROM workflow_node_runs WHERE workflow_run_id = ?",
        (workflow_run_id,),
    ).fetchone()
    total = int(count_row["total"]) if count_row else 0
    rows = connection.execute(
        "SELECT * FROM workflow_node_runs WHERE workflow_run_id = ? ORDER BY rowid LIMIT ? OFFSET ?",
        (workflow_run_id, limit, offset),
    ).fetchall()
    return decode_rows(rows), total


def get_latest_project_workflow_run(connection: sqlite3.Connection, project_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT wr.*
        FROM workflow_runs wr
        JOIN design_tasks dt ON dt.task_id = wr.task_id
        WHERE dt.project_id = ?
        ORDER BY wr.start_time DESC, wr.rowid DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    return get_by_id(connection, "workflow_runs", "workflow_run_id", row["workflow_run_id"]) if row else None


def list_project_workflow_runs(connection: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT wr.*, p.selected_route
        FROM workflow_runs wr
        JOIN design_tasks dt ON dt.task_id = wr.task_id
        LEFT JOIN workflow_plans p ON p.materialized_workflow_run_id = wr.workflow_run_id
        WHERE dt.project_id = ?
        ORDER BY wr.start_time DESC, wr.rowid DESC
        """,
        (project_id,),
    ).fetchall()
    return decode_rows(rows)


def get_project_candidate_funnel(connection: sqlite3.Connection, project_id: str) -> dict[str, int]:
    run = get_latest_project_workflow_run(connection, project_id)
    if run is None:
        return {"generated": 0, "designed": 0, "folded": 0, "scored": 0, "ordered": 0}
    metrics = run.get("summary_metrics_json") or {}
    if isinstance(metrics, str):
        metrics = json.loads(metrics)
    return {
        "generated": int(metrics.get("generated", 0)),
        "designed": int(metrics.get("designed", 0)),
        "folded": int(metrics.get("folded", 0)),
        "scored": int(metrics.get("scored", 0)),
        "ordered": int(metrics.get("ordered", 0)),
    }


def get_project_delivery_package(connection: sqlite3.Connection, project_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT * FROM delivery_packages
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if row is None:
        return None
    return decode_row(row)


def _parse_kd_nM(value: str | None) -> float | None:
    if not value:
        return None
    match = KD_VALUE_RE.search(value)
    if not match:
        return None
    return float(match.group(1))


def get_project_results_summary(connection: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    results = list_project_experiment_results(connection, project_id)
    funnel = get_project_candidate_funnel(connection, project_id)
    ordered = funnel["ordered"]

    bli_results = [r for r in results if r.get("experiment_type") == "BLI"]
    bli_pass = [r for r in bli_results if r.get("pass_status") == "pass"]
    sec_failures = [r for r in results if r.get("experiment_type") == "SEC" and r.get("pass_status") == "fail"]

    best_candidate = None
    best_kd = None
    for result in bli_pass:
        kd = _parse_kd_nM(result.get("value"))
        if kd is None:
            continue
        if best_kd is None or kd < best_kd:
            best_kd = kd
            best_candidate = result.get("candidate_id")

    hit_count = len({r["candidate_id"] for r in bli_pass})
    hit_rate_pct = round((hit_count / ordered) * 100, 1) if ordered else 0.0

    package = get_project_delivery_package(connection, project_id)
    constraints = (package or {}).get("redesign_constraints") or {}
    if isinstance(constraints, str):
        constraints = json.loads(constraints)

    preserve = constraints.get("preserve_candidate", best_candidate or "")
    decision_detail = (
        f"Preserve {preserve} motif and penalize hydrophobic patches"
        if constraints.get("penalize_exposed_hydrophobic_area")
        else "Continue round-two optimization with current constraints"
    )

    return {
        "hit_count": hit_count,
        "ordered_count": ordered,
        "hit_rate_pct": hit_rate_pct,
        "hit_rate_label": f"{hit_count}/{ordered} candidates validated (BLI)",
        "best_kd": f"{best_kd} nM" if best_kd is not None else "—",
        "best_kd_candidate": best_candidate,
        "main_failure": "SEC",
        "main_failure_detail": "Aggregation explains most QC loss",
        "sec_failure_count": len(sec_failures),
        "decision": "Round 2",
        "decision_detail": decision_detail,
        "experiment_summary": (package or {}).get("experiment_summary"),
    }


def candidate_belongs_to_project(connection: sqlite3.Connection, candidate_id: str, project_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM candidates WHERE candidate_id = ? AND project_id = ? LIMIT 1",
        (candidate_id, project_id),
    ).fetchone()
    return row is not None


def get_project_overview(connection: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    project = get_project(connection, project_id)
    if project is None:
        return None

    from . import registry

    funnel = get_project_candidate_funnel(connection, project_id)
    results_summary = get_project_results_summary(connection, project_id)
    run = get_latest_project_workflow_run(connection, project_id)

    compute_nodes = registry.list_compute_nodes(connection)
    gpu_available = any(
        n.get("status") == "available" and n.get("node_type") == "GPU" for n in compute_nodes
    )
    cpu_available = any(
        n.get("status") == "available" and n.get("node_type") == "CPU" for n in compute_nodes
    )

    if gpu_available or cpu_available:
        compute_label = "Workers connected"
    else:
        compute_label = "Compute not connected (demo mode)"

    if run and run.get("status") == "completed":
        next_action = "Review candidates and interpret BLI/SEC results for round two."
    elif run and run.get("status") == "draft":
        next_action = "Finish workflow layout and submit to compute."
    else:
        next_action = "Create a workflow route for this project."

    return {
        "project": project,
        "funnel": funnel,
        "results_summary": results_summary if funnel["ordered"] else None,
        "compute_status": {
            "gpu_available": gpu_available,
            "cpu_available": cpu_available,
            "label": compute_label,
        },
        "next_action": next_action,
    }


def get_project_design_task(connection: sqlite3.Connection, project_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM design_tasks WHERE project_id = ? ORDER BY rowid DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if row is None:
        return None
    return decode_row(row)


def create_draft_workflow_run(connection: sqlite3.Connection, project_id: str) -> dict:
    import uuid

    task = get_project_design_task(connection, project_id)
    if task is None:
        task_id = f"task_{project_id}_draft"
        connection.execute(
            """
            INSERT INTO design_tasks (task_id, project_id, task_type, objective, status, created_by)
            VALUES (?, ?, 'binder_design', 'Draft workflow route', 'draft', 'demo-user')
            """,
            (task_id, project_id),
        )
    else:
        task_id = task["task_id"]

    workflow_run_id = f"run_{project_id}_{uuid.uuid4().hex[:8]}"
    connection.execute(
        """
        INSERT INTO workflow_runs (workflow_run_id, task_id, status, compute_resource, summary_metrics_json, layout_json)
        VALUES (?, ?, 'draft', 'local', '{}', '{"nodes":[],"edges":[]}')
        """,
        (workflow_run_id, task_id),
    )
    return get_workflow_run(connection, workflow_run_id) or {}


def add_workflow_node(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    *,
    node_type: str,
    node_name: str,
    model_name: str | None = None,
    model_version: str | None = None,
    parameters_json: str = "{}",
    position_json: str = '{"x":0,"y":0}',
) -> dict:
    import uuid

    node_run_id = f"node_{uuid.uuid4().hex[:10]}"
    connection.execute(
        """
        INSERT INTO workflow_node_runs (
            node_run_id, workflow_run_id, node_type, node_name, status,
            model_name, model_version, parameters_json, position_json
        ) VALUES (?, ?, ?, ?, 'not_started', ?, ?, ?, ?)
        """,
        (
            node_run_id,
            workflow_run_id,
            node_type,
            node_name,
            model_name,
            model_version,
            parameters_json,
            position_json,
        ),
    )
    return get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id) or {}


def update_workflow_node(
    connection: sqlite3.Connection,
    node_run_id: str,
    *,
    position_json: str | None = None,
    parameters_json: str | None = None,
    input_files_json: str | None = None,
    output_files_json: str | None = None,
    metrics_json: str | None = None,
    status: str | None = None,
    error_message: str | None = None,
) -> dict | None:
    updates: list[str] = []
    params: list[object] = []
    if position_json is not None:
        updates.append("position_json = ?")
        params.append(position_json)
    if parameters_json is not None:
        updates.append("parameters_json = ?")
        params.append(parameters_json)
    if input_files_json is not None:
        updates.append("input_files_json = ?")
        params.append(input_files_json)
    if output_files_json is not None:
        updates.append("output_files_json = ?")
        params.append(output_files_json)
    if metrics_json is not None:
        updates.append("metrics_json = ?")
        params.append(metrics_json)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if not updates:
        return get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)
    params.append(node_run_id)
    connection.execute(
        f"UPDATE workflow_node_runs SET {', '.join(updates)} WHERE node_run_id = ?",
        params,
    )
    return get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)


def delete_workflow_node(connection: sqlite3.Connection, node_run_id: str) -> bool:
    cursor = connection.execute(
        "DELETE FROM workflow_node_runs WHERE node_run_id = ?",
        (node_run_id,),
    )
    return cursor.rowcount > 0


def save_workflow_layout(connection: sqlite3.Connection, workflow_run_id: str, layout_json: str) -> dict | None:
    connection.execute(
        "UPDATE workflow_runs SET layout_json = ? WHERE workflow_run_id = ?",
        (layout_json, workflow_run_id),
    )
    return get_workflow_run(connection, workflow_run_id)


def upsert_target_upload(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    filename: str,
    structure_file_path: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    existing = connection.execute(
        "SELECT target_id FROM targets WHERE project_id = ? ORDER BY rowid LIMIT 1",
        (project_id,),
    ).fetchone()
    metadata_json = json.dumps(
        {
            **metadata,
            "upload_filename": filename,
            "source": "upload-pdb",
        }
    )
    target_name = Path(filename).stem if filename else "Uploaded structure"

    if existing:
        target_id = existing["target_id"]
        connection.execute(
            """
            UPDATE targets
            SET target_name = ?, chain_ids = ?, structure_file_path = ?, metadata_json = ?
            WHERE target_id = ?
            """,
            (
                target_name,
                ",".join(metadata.get("chains", [])) or "A",
                structure_file_path,
                metadata_json,
                target_id,
            ),
        )
    else:
        target_id = f"target_{project_id}_upload"
        connection.execute(
            """
            INSERT INTO targets (
                target_id, project_id, target_name, target_type,
                chain_ids, structure_file_path, metadata_json
            ) VALUES (?, ?, ?, 'protein', ?, ?, ?)
            """,
            (
                target_id,
                project_id,
                target_name,
                ",".join(metadata.get("chains", [])) or "A",
                structure_file_path,
                metadata_json,
            ),
        )

    return get_by_id(connection, "targets", "target_id", target_id) or {}
