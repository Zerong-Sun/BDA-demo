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
    jobs = job_service.submit_workflow_jobs(
        connection, workflow_run_id, payload.compute_node_id
    )
    if not jobs:
        from ..compute.factory import get_compute_adapter
        from ..compute.adapter import JobSpec
        import uuid

        adapter = get_compute_adapter()
        demo_id = f"job_{uuid.uuid4().hex[:8]}"
        spec = JobSpec(
            job_id=demo_id,
            workflow_run_id=workflow_run_id,
            node_run_id=None,
            plugin_id="demo",
            container_image="bda/demo:latest",
            command="echo demo",
        )
        handle = adapter.submit(spec)
        st = adapter.status(demo_id, handle.external_id)
        return envelope({
            "workflow_run_id": workflow_run_id,
            "status": st.status,
            "reason": "compute_not_connected" if st.status == "blocked" else None,
            "message": st.logs or "Workflow submitted.",
            "job_ids": [demo_id] if st.status != "blocked" else [],
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return envelope({
        "node_run_id": node_run_id,
        "job_id": job.get("job_id"),
        "status": job.get("status", "queued"),
    })
