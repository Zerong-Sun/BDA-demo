import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth.deps import get_current_user, require_node_run_access, require_workflow_run_access
from ..db import get_connection
from ..services import job_service
from ..utils.response import envelope

router = APIRouter()


class SubmitWorkflowRequest(BaseModel):
    compute_node_id: str | None = None
    priority: int | None = None


class SubmitNodeRequest(BaseModel):
    compute_node_id: str | None = None
    override_params: dict | None = None


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
        job = job_service.submit_node_job(connection, node_run_id, payload.compute_node_id)
    except ValueError as exc:
        detail = str(exc)
        status = 404 if detail == "node_not_found" else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return envelope({
        "node_run_id": node_run_id,
        "job_id": job.get("job_id"),
        "status": job.get("status", "queued"),
    })
