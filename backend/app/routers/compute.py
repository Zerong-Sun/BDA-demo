import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth.deps import get_current_user, require_node_run_access, require_workflow_run_access
from ..db import get_connection
from ..services import job_service
from ..schemas import AutomationPolicyUpdateRequest
from ..utils.response import envelope

router = APIRouter()


class SubmitWorkflowRequest(BaseModel):
    compute_node_id: str | None = None
    priority: int | None = None


class SubmitNodeRequest(BaseModel):
    compute_node_id: str | None = None
    expected_parameter_checksum: str | None = None


@router.get("/compute/cluster-health")
def cluster_health(
    _user: dict = Depends(get_current_user),
):
    from ..compute.factory import get_compute_adapter
    from ..settings import get_settings

    adapter = get_compute_adapter()
    health = getattr(adapter, "health", None)
    if not callable(health):
        return envelope({
            "mode": get_settings().bda_compute_mode,
            "connected": False,
            "queues": [],
            "reason": "remote_cluster_adapter_not_enabled",
        })
    try:
        return envelope(health())
    except RuntimeError as exc:
        return envelope({
            "mode": "remote_lsf",
            "connected": False,
            "queues": [],
            "reason": str(exc),
        })


@router.get("/workflow-runs/{workflow_run_id}/automation-policy")
def get_workflow_automation_policy(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    from ..repositories import automation

    item = automation.get_policy(connection, workflow_run_id)
    return envelope(item or {
        "workflow_run_id": workflow_run_id,
        "mode": "confirm_each_node",
        "auto_submit_ready": False,
        "notify_on_ready": True,
        "notify_on_terminal": True,
        "max_auto_retries": 0,
        "retry_backoff_seconds": 60,
    })


@router.patch("/workflow-runs/{workflow_run_id}/automation-policy")
def update_workflow_automation_policy(
    workflow_run_id: str,
    payload: AutomationPolicyUpdateRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(require_workflow_run_access),
):
    from ..repositories import automation

    if payload.auto_submit_ready and payload.mode != "auto_after_gate":
        raise HTTPException(status_code=400, detail="auto_submit_requires_auto_after_gate_mode")
    item = automation.upsert_policy(
        connection,
        workflow_run_id=workflow_run_id,
        created_by=user["user_id"],
        **payload.model_dump(),
    )
    return envelope(item)


@router.post("/workflow-runs/{workflow_run_id}/evaluate-ready-nodes")
def evaluate_workflow_ready_nodes(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    from ..services.run_coordinator import evaluate_downstream_nodes

    return envelope(evaluate_downstream_nodes(
        connection,
        workflow_run_id=workflow_run_id,
    ))


@router.post("/workflow-runs/{workflow_run_id}/submit-to-compute")
def submit_workflow_run(
    workflow_run_id: str,
    payload: SubmitWorkflowRequest | None = None,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    payload = payload or SubmitWorkflowRequest()
    jobs = job_service.submit_workflow_jobs(connection, workflow_run_id, payload.compute_node_id)
    if not jobs:
        return envelope({
            "workflow_run_id": workflow_run_id,
            "status": "blocked",
            "reason": "no_submittable_nodes",
            "message": "No pending workflow nodes to submit, or compute is in demo mode.",
            "job_ids": [],
        })
    from ..services.campaign_service import sync_round_status

    campaign_round = sync_round_status(connection, workflow_run_id)
    return envelope({
        "workflow_run_id": workflow_run_id,
        "status": "queued",
        "job_ids": [j["job_id"] for j in jobs],
        "campaign_round": campaign_round,
    })


@router.post("/workflow-node-runs/{node_run_id}/submit-to-compute")
def submit_workflow_node(
    node_run_id: str,
    payload: SubmitNodeRequest | None = None,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_node_run_access),
):
    from ..repositories import catalog

    node = catalog.get_workflow_node(connection, node_run_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node_not_found")

    payload = payload or SubmitNodeRequest()
    try:
        job = job_service.submit_node_job(
            connection,
            node_run_id,
            payload.compute_node_id,
            expected_parameter_checksum=payload.expected_parameter_checksum,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 404 if detail == "node_not_found" else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return envelope({
        "node_run_id": node_run_id,
        "job_id": job.get("job_id"),
        "status": job.get("status", "queued"),
    })


@router.get("/workflow-node-runs/{node_run_id}/submission-preview")
def preview_workflow_node_submission(
    node_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_node_run_access),
):
    try:
        return envelope(job_service.preview_node_submission(connection, node_run_id))
    except ValueError as exc:
        status = 404 if str(exc) == "node_not_found" else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/workflow-node-runs/{node_run_id}/complete-review")
def complete_manual_workflow_node(
    node_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_node_run_access),
):
    from ..repositories import catalog, registry

    node = catalog.get_workflow_node(connection, node_run_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node_not_found")
    registered_models = {item.get("model_name") for item in registry.list_model_plugins(connection)}
    if node.get("model_name") in registered_models:
        raise HTTPException(status_code=400, detail="compute_node_requires_job_submission")
    if node.get("status") == "completed":
        return envelope(node)
    allowed_manual_types = {
        "research_review",
        "structure_preparation",
        "review_gate",
        "selection",
    }
    if node.get("node_type") not in allowed_manual_types:
        raise HTTPException(
            status_code=400,
            detail="manual_node_requires_external_result_or_specialized_completion",
        )
    incoming = [
        edge
        for edge in catalog.list_workflow_edges(connection, node["workflow_run_id"])
        if edge.get("target_node_run_id") == node_run_id
        and edge.get("edge_type", "data") in {"data", "control", "review_gate"}
    ]
    incomplete = []
    for edge in incoming:
        source = catalog.get_workflow_node(connection, edge["source_node_run_id"])
        if source is None or source.get("status") != "completed":
            incomplete.append(edge["source_node_run_id"])
    if incomplete:
        raise HTTPException(
            status_code=409,
            detail=f"upstream_review_not_completed:{','.join(incomplete)}",
        )
    item = catalog.update_workflow_node(connection, node_run_id, status="completed")
    connection.execute(
        """
        UPDATE decision_gates
        SET status='approved', reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        WHERE node_run_id = ?
        """,
        (_user["user_id"], node_run_id),
    )
    from ..services.run_coordinator import evaluate_downstream_nodes

    evaluate_downstream_nodes(
        connection,
        workflow_run_id=node["workflow_run_id"],
        completed_node_run_id=node_run_id,
    )
    return envelope(item)
