import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


@router.post("/workflow-runs/{workflow_run_id}/submit-to-compute")
def submit_workflow_run(
    workflow_run_id: str,
    payload: SubmitWorkflowRequest | None = None,
    connection: sqlite3.Connection = Depends(get_connection),
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
    return envelope({
        "workflow_run_id": workflow_run_id,
        "status": "queued",
        "job_ids": [j["job_id"] for j in jobs],
    })


@router.post("/workflow-node-runs/{node_run_id}/submit-to-compute")
def submit_workflow_node(
    node_run_id: str,
    payload: SubmitNodeRequest | None = None,
    connection: sqlite3.Connection = Depends(get_connection),
):
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
