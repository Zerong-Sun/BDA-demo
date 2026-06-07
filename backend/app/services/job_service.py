from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from ..compute.adapter import JobSpec
from ..compute.factory import get_compute_adapter
from ..repositories import catalog, registry
from ..repositories.base import decode_row, decode_rows, get_by_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str | None,
    node_run_id: str | None,
    plugin_id: str,
    input_artifacts: dict[str, Any] | None = None,
    compute_node_id: str | None = None,
) -> dict[str, Any]:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO jobs (
            job_id, workflow_run_id, node_run_id, compute_node_id,
            status, plugin_id, input_artifacts, output_artifacts, created_at
        ) VALUES (?, ?, ?, ?, 'queued', ?, ?, '{}', ?)
        """,
        (
            job_id,
            workflow_run_id,
            node_run_id,
            compute_node_id,
            plugin_id,
            json.dumps(input_artifacts or {}),
            _now_iso(),
        ),
    )
    connection.commit()
    return get_job(connection, job_id) or {}


def get_job(connection: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return decode_row(row)


def list_workflow_jobs(connection: sqlite3.Connection, workflow_run_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM jobs WHERE workflow_run_id = ? ORDER BY created_at",
        (workflow_run_id,),
    ).fetchall()
    return decode_rows(rows)


def update_job_status(
    connection: sqlite3.Connection,
    job_id: str,
    *,
    status: str,
    logs: str | None = None,
    output_artifacts: dict | None = None,
    error_message: str | None = None,
    external_id: str | None = None,
) -> dict[str, Any] | None:
    updates = ["status = ?"]
    params: list[Any] = [status]
    if logs is not None:
        updates.append("logs = ?")
        params.append(logs)
    if output_artifacts is not None:
        updates.append("output_artifacts = ?")
        params.append(json.dumps(output_artifacts))
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if external_id is not None:
        updates.append("external_id = ?")
        params.append(external_id)
    if status == "running":
        updates.append("started_at = ?")
        params.append(_now_iso())
    if status in ("completed", "failed", "cancelled"):
        updates.append("finished_at = ?")
        params.append(_now_iso())
    params.append(job_id)
    connection.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params)
    connection.commit()
    return get_job(connection, job_id)


def _plugin_runtime_env(plugin: dict | None) -> dict[str, str]:
    if not plugin:
        return {}
    requirements = plugin.get("resource_requirement_json") or {}
    if isinstance(requirements, str):
        requirements = json.loads(requirements)
    env = dict((requirements.get("runtime_env") or {}))
    gpu_count = requirements.get("gpu_count") or 0
    if gpu_count:
        env.setdefault("BDA_GPU", "1")
    return env


def _enqueue_poll(job_id: str) -> None:
    try:
        from ..celery_app import poll_job_status

        poll_job_status.delay(job_id)
    except Exception:
        pass


def submit_node_job(connection: sqlite3.Connection, node_run_id: str, compute_node_id: str | None = None) -> dict:
    node = get_by_id(connection, "workflow_node_runs", "node_run_id", node_run_id)
    if node is None:
        raise ValueError("node_not_found")

    plugin = None
    if node.get("model_name"):
        plugins = registry.list_model_plugins(connection)
        plugin = next((p for p in plugins if p.get("model_name") == node.get("model_name")), None)

    plugin_id = (plugin or {}).get("model_plugin_id", "unknown")
    job = create_job(
        connection,
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node_run_id,
        plugin_id=plugin_id,
        input_artifacts=node.get("input_files_json") or {},
        compute_node_id=compute_node_id,
    )

    runtime_env = _plugin_runtime_env(plugin)
    container_image = (plugin or {}).get("container_image") or "bda/demo:latest"
    command = (plugin or {}).get("command_template") or "echo demo"

    spec = JobSpec(
        job_id=job["job_id"],
        workflow_run_id=node.get("workflow_run_id"),
        node_run_id=node_run_id,
        plugin_id=plugin_id,
        container_image=container_image,
        command=command,
        input_artifacts=node.get("input_files_json") or {},
        compute_node_id=compute_node_id,
        env=runtime_env,
    )
    adapter = get_compute_adapter()
    try:
        handle = adapter.submit(spec)
    except RuntimeError as exc:
        update_job_status(connection, job["job_id"], status="failed", error_message=str(exc))
        raise ValueError(str(exc)) from exc

    st = adapter.status(job["job_id"], handle.external_id)
    update_job_status(
        connection,
        job["job_id"],
        status=st.status if st.status != "blocked" else "queued",
        logs=st.logs,
        external_id=handle.external_id,
    )
    if st.status not in ("blocked", "failed"):
        catalog.update_workflow_node(connection, node_run_id, status="queued")
    _enqueue_poll(job["job_id"])

    return get_job(connection, job["job_id"]) or job


def submit_workflow_jobs(connection: sqlite3.Connection, workflow_run_id: str, compute_node_id: str | None = None) -> list[dict]:
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    jobs = []
    for node in nodes:
        if node.get("status") in ("completed", "running", "queued"):
            continue
        try:
            job = submit_node_job(connection, node["node_run_id"], compute_node_id)
            jobs.append(job)
        except ValueError:
            continue
    return jobs
