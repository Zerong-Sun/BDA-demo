import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth.deps import require_job_access, require_workflow_run_access
from ..compute.factory import get_compute_adapter
from ..db import get_connection
from ..services import job_service
from ..utils.response import envelope

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_job_access),
):
    job = job_service.get_job(connection, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    adapter = get_compute_adapter()
    if job.get("external_id"):
        live = adapter.status(job_id, job.get("external_id"))
        if live.status not in ("blocked", "not_found") and live.status != job.get("status"):
            job = job_service.update_job_status(
                connection,
                job_id,
                status=live.status,
                logs=live.logs,
                output_artifacts=live.output_artifacts or None,
                error_message=live.error_message,
            ) or job
    return envelope(job)


@router.get("/jobs/{job_id}/logs")
def job_logs(
    job_id: str,
    tail: int = 200,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_job_access),
):
    job = job_service.get_job(connection, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    adapter = get_compute_adapter()
    logs = adapter.logs(job_id, job.get("external_id"), tail=tail)
    if not logs and job.get("logs"):
        logs = job["logs"]
    return envelope({"job_id": job_id, "logs": logs})


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_job_access),
):
    job = job_service.get_job(connection, job_id)
    if job is None:
        return envelope({"job_id": job_id, "status": "not_found", "demo_mode": True})
    adapter = get_compute_adapter()
    cancelled = adapter.cancel(job_id, job.get("external_id"))
    if cancelled:
        job_service.update_job_status(connection, job_id, status="cancelled")
        return envelope({"job_id": job_id, "status": "cancelled"})
    return envelope({"job_id": job_id, "status": job.get("status"), "cancelled": False})


@router.get("/workflow-runs/{workflow_run_id}/jobs")
def workflow_jobs(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    return envelope({"items": job_service.list_workflow_jobs(connection, workflow_run_id)})
