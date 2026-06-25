import sqlite3
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.deps import (
    get_current_user,
    require_candidate_access,
    require_project_access,
    require_workflow_run_access,
)
from ..db import get_connection
from ..repositories import catalog
from ..schemas import CreateProjectRequest
from ..utils.response import envelope

router = APIRouter()


@router.get("/health")
def health():
    from ..settings import get_settings

    s = get_settings()
    return envelope({
        "status": "ok",
        "service": "bda-api-gateway",
        "compute": s.bda_compute_mode,
        "database": "postgresql" if s.is_postgresql else "sqlite",
    })


@router.get("/projects/{project_id}/overview")
def project_overview(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    item = catalog.get_project_overview(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return envelope(item)


@router.get("/projects")
def projects(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items, total = catalog.list_projects_paginated(connection, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.post("/projects")
def create_project(
    payload: CreateProjectRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    name = payload.project_name.strip()
    project_type = payload.project_type.strip()
    if not name or not project_type:
        raise HTTPException(status_code=422, detail="project_name_and_type_required")
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30] or "project"
    project_id = f"proj_{slug}_{uuid.uuid4().hex[:6]}"
    organization = connection.execute(
        "SELECT organization_id FROM organization_members WHERE user_id = ? LIMIT 1",
        (user.get("user_id"),),
    ).fetchone()
    item = catalog.create_project(
        connection,
        project_id=project_id,
        project_name=name,
        project_type=project_type,
        owner_id=user.get("user_id"),
        organization_id=organization["organization_id"] if organization else None,
        summary=payload.summary.strip() if payload.summary else None,
    )
    return envelope(item)


@router.get("/projects/{project_id}")
def project(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
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
    _user: dict = Depends(require_project_access),
):
    try:
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/candidates/{candidate_id}")
def candidate(
    candidate_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_candidate_access),
):
    item = catalog.get_candidate(connection, candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/experiment-results")
def project_experiment_results(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    return envelope(catalog.list_project_experiment_results(connection, project_id))


@router.get("/projects/{project_id}/candidate-funnel")
def project_candidate_funnel(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    return envelope(catalog.get_project_candidate_funnel(connection, project_id))


@router.get("/projects/{project_id}/results-summary")
def project_results_summary(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    return envelope(catalog.get_project_results_summary(connection, project_id))


@router.get("/projects/{project_id}/delivery-package")
def project_delivery_package(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    item = catalog.get_project_delivery_package(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="delivery_package_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/workflow-runs/latest")
def project_latest_workflow_run(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    item = catalog.get_latest_project_workflow_run(connection, project_id)
    if item is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return envelope(item)


@router.get("/projects/{project_id}/workflow-runs")
def project_workflow_runs(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    items = catalog.list_project_workflow_runs(connection, project_id)
    return envelope({
        "items": items,
        "total": len(items),
        "limit": len(items),
        "offset": 0,
    })


@router.get("/workflow-runs/{workflow_run_id}")
def workflow_run(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    item = catalog.get_workflow_run(connection, workflow_run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return envelope(item)


@router.get("/workflow-runs/{workflow_run_id}/nodes")
def workflow_nodes(
    workflow_run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    items, total = catalog.list_workflow_nodes_paginated(
        connection, workflow_run_id, limit=limit, offset=offset
    )
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/workflow-runs/{workflow_run_id}/logs")
def workflow_logs(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    return envelope([
        {"node_run_id": node["node_run_id"], "node_name": node["node_name"], "logs": node["logs"]}
        for node in nodes
    ])
