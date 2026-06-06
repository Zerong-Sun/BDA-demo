import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_connection
from ..repositories import catalog

router = APIRouter()


def envelope(data):
    return {"data": data, "trace_id": str(uuid4())}


@router.get("/health")
def health():
    return envelope({"status": "ok", "service": "bda-api-gateway", "compute": "demo"})


@router.get("/projects")
def projects(connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(catalog.list_projects(connection))


@router.get("/projects/{project_id}")
def project(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = catalog.get_project(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/candidates")
def project_candidates(
    project_id: str,
    sort: str = "interface_score",
    order: str = "desc",
    status: str | None = None,
    decision: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    connection: sqlite3.Connection = Depends(get_connection),
):
    items, total = catalog.list_project_candidates_filtered(
        connection,
        project_id,
        sort=sort,
        order=order,
        status=status,
        decision=decision,
        search=search,
        limit=min(max(limit, 1), 200),
        offset=max(offset, 0),
    )
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/candidates/{candidate_id}")
def candidate(candidate_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = catalog.get_candidate(connection, candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/experiment-results")
def project_experiment_results(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(catalog.list_project_experiment_results(connection, project_id))


@router.get("/projects/{project_id}/candidate-funnel")
def project_candidate_funnel(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(catalog.get_project_candidate_funnel(connection, project_id))


@router.get("/projects/{project_id}/results-summary")
def project_results_summary(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(catalog.get_project_results_summary(connection, project_id))


@router.get("/projects/{project_id}/delivery-package")
def project_delivery_package(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = catalog.get_project_delivery_package(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="delivery_package_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/workflow-runs/latest")
def project_latest_workflow_run(project_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = catalog.get_latest_project_workflow_run(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return envelope(item)


@router.get("/workflow-runs/{workflow_run_id}")
def workflow_run(workflow_run_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = catalog.get_workflow_run(connection, workflow_run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return envelope(item)


@router.get("/workflow-runs/{workflow_run_id}/nodes")
def workflow_nodes(workflow_run_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(catalog.list_workflow_nodes(connection, workflow_run_id))


@router.get("/workflow-runs/{workflow_run_id}/logs")
def workflow_logs(workflow_run_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    return envelope([{"node_run_id": node["node_run_id"], "node_name": node["node_name"], "logs": node["logs"]} for node in nodes])

