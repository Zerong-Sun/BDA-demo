from __future__ import annotations

import sqlite3
from typing import Any

from ..repositories import automation, catalog


TERMINAL = {
    "completed",
    "failed",
    "failed_retryable",
    "failed_terminal",
    "cancelled",
}


def _project_id(connection: sqlite3.Connection, workflow_run_id: str) -> str | None:
    return catalog.get_workflow_run_project_id(connection, workflow_run_id)


def evaluate_downstream_nodes(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    completed_node_run_id: str | None = None,
) -> dict[str, Any]:
    policy = automation.get_policy(connection, workflow_run_id) or {
        "mode": "confirm_each_node",
        "auto_submit_ready": False,
        "notify_on_ready": True,
        "notify_on_terminal": True,
        "max_auto_retries": 0,
    }
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    edges = catalog.list_workflow_edges(connection, workflow_run_id)
    nodes_by_id = {node["node_run_id"]: node for node in nodes}
    ready: list[dict[str, Any]] = []
    waiting_external: list[dict[str, Any]] = []
    for node in nodes:
        if node.get("status") in TERMINAL | {"queued", "running", "staging"}:
            continue
        incoming = [
            edge for edge in edges
            if edge.get("target_node_run_id") == node["node_run_id"]
            and edge.get("edge_type", "data") in {"data", "control", "review_gate"}
        ]
        if incoming and not all(
            nodes_by_id.get(edge["source_node_run_id"], {}).get("status") == "completed"
            for edge in incoming
        ):
            continue
        if node.get("node_type") == "experiment":
            if node.get("status") != "waiting_external_result":
                catalog.update_workflow_node(
                    connection,
                    node["node_run_id"],
                    status="waiting_external_result",
                )
            waiting_external.append(node)
            continue
        next_status = "requires_review" if (
            (node.get("parameters_json") or {}).get("requires_user_review")
            or not node.get("model_name")
        ) else "ready"
        if node.get("status") != next_status:
            catalog.update_workflow_node(
                connection,
                node["node_run_id"],
                status=next_status,
            )
        ready.append({**node, "status": next_status})
    project_id = _project_id(connection, workflow_run_id)
    if policy.get("notify_on_ready"):
        for node in ready:
            automation.create_notification(
                connection,
                user_id=policy.get("created_by"),
                project_id=project_id,
                workflow_run_id=workflow_run_id,
                node_run_id=node["node_run_id"],
                notification_type="node_ready",
                title=f"{node['node_name']} is ready",
                message=(
                    "Review parameters and confirm submission."
                    if node["status"] == "requires_review"
                    else "Node inputs and upstream gates are complete."
                ),
                metadata={"completed_node_run_id": completed_node_run_id},
                dedupe_unread=True,
            )
    auto_submitted: list[str] = []
    if policy.get("auto_submit_ready") and policy.get("mode") == "auto_after_gate":
        from . import job_service

        for node in ready:
            if node["status"] != "ready" or not node.get("model_name"):
                continue
            try:
                job = job_service.submit_node_job(connection, node["node_run_id"])
                auto_submitted.append(job["job_id"])
            except ValueError:
                continue
    return {
        "ready_nodes": [node["node_run_id"] for node in ready],
        "waiting_external_nodes": [node["node_run_id"] for node in waiting_external],
        "auto_submitted_job_ids": auto_submitted,
        "policy": policy,
    }


def handle_job_terminal(
    connection: sqlite3.Connection,
    *,
    job: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    workflow_run_id = job.get("workflow_run_id")
    node_run_id = job.get("node_run_id")
    if not workflow_run_id:
        return {}
    policy = automation.get_policy(connection, workflow_run_id) or {}
    project_id = _project_id(connection, workflow_run_id)
    if policy.get("notify_on_terminal", True):
        automation.create_notification(
            connection,
            user_id=policy.get("created_by"),
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            notification_type=f"job_{status}",
            title=f"Compute job {status}",
            message=f"Job {job.get('job_id')} for node {node_run_id} is {status}.",
            metadata={"job_id": job.get("job_id")},
            dedupe_unread=True,
        )
    if status == "completed":
        return evaluate_downstream_nodes(
            connection,
            workflow_run_id=workflow_run_id,
            completed_node_run_id=node_run_id,
        )
    if status == "failed" and node_run_id:
        failed_count = connection.execute(
            "SELECT COUNT(*) AS count FROM jobs WHERE node_run_id = ? AND status = 'failed'",
            (node_run_id,),
        ).fetchone()["count"]
        retry_limit = int(policy.get("max_auto_retries") or 0)
        retryable = failed_count <= retry_limit
        catalog.update_workflow_node(
            connection,
            node_run_id,
            status="failed_retryable" if retryable else "failed_terminal",
        )
        automation.create_notification(
            connection,
            user_id=policy.get("created_by"),
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            node_run_id=node_run_id,
            notification_type="retry_recommended" if retryable else "retry_limit_reached",
            title="Compute retry available" if retryable else "Compute retry limit reached",
            message=(
                "Review the failure log and resubmit this node after confirming its parameters."
                if retryable
                else "The configured retry limit has been reached; manual diagnosis is required."
            ),
            metadata={
                "job_id": job.get("job_id"),
                "failed_attempts": failed_count,
                "max_auto_retries": retry_limit,
            },
            dedupe_unread=True,
        )
        return {"status": status, "retry_suggestion": retryable}
    return {"status": status, "retry_suggestion": False}
