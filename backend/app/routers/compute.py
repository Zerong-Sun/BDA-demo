from uuid import uuid4

from fastapi import APIRouter

router = APIRouter()


def envelope(data):
    return {"data": data, "trace_id": str(uuid4())}


@router.post("/workflow-runs/{workflow_run_id}/submit-to-compute")
def submit_workflow_run(workflow_run_id: str):
    return envelope({
        "workflow_run_id": workflow_run_id,
        "status": "blocked",
        "reason": "compute_not_connected",
        "message": "MVP API gateway is running, but CPU/GPU worker adapters are not connected.",
    })


@router.post("/workflow-node-runs/{node_run_id}/submit-to-compute")
def submit_workflow_node(node_run_id: str):
    return envelope({
        "node_run_id": node_run_id,
        "status": "blocked",
        "reason": "compute_not_connected",
    })


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    return envelope({"job_id": job_id, "status": "not_found", "demo_mode": True})

