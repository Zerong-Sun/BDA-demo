import sqlite3
import re

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
    queue_name: str | None = None
    cpu_count: int | None = None
    resource_requirement: str | None = None
    gpu_requirement: str | None = None


class SubmitNodeRequest(BaseModel):
    compute_node_id: str | None = None
    override_params: dict | None = None
    queue_name: str | None = None
    cpu_count: int | None = None
    resource_requirement: str | None = None
    gpu_requirement: str | None = None


QUEUE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
LSF_SAFE_RE = re.compile(r"^[A-Za-z0-9_.,=:+\\-\\[\\]()/ <>!*&|]+$")


def _validate_lsf_overrides(payload: SubmitWorkflowRequest | SubmitNodeRequest) -> None:
    if payload.queue_name and not QUEUE_RE.fullmatch(payload.queue_name):
        raise HTTPException(status_code=422, detail="invalid_queue_name")
    if payload.cpu_count is not None and not (1 <= payload.cpu_count <= 256):
        raise HTTPException(status_code=422, detail="invalid_cpu_count")
    for field in ("resource_requirement", "gpu_requirement"):
        value = getattr(payload, field)
        if value and (len(value) > 240 or not LSF_SAFE_RE.fullmatch(value)):
            raise HTTPException(status_code=422, detail=f"invalid_{field}")


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
    _validate_lsf_overrides(payload)
    jobs = job_service.submit_workflow_jobs(
        connection,
        workflow_run_id,
        payload.compute_node_id,
        queue_name=payload.queue_name,
        cpu_count=payload.cpu_count,
        resource_requirement=payload.resource_requirement,
        gpu_requirement=payload.gpu_requirement,
    )
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
    _validate_lsf_overrides(payload)
    try:
        job = job_service.submit_node_job(
            connection,
            node_run_id,
            payload.compute_node_id,
            queue_name=payload.queue_name,
            cpu_count=payload.cpu_count,
            resource_requirement=payload.resource_requirement,
            gpu_requirement=payload.gpu_requirement,
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
