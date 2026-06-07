import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import require_project_access, require_workflow_run_access
from ..db import get_connection
from ..repositories import catalog
from ..utils.response import envelope

router = APIRouter()


class AddWorkflowNodeRequest(BaseModel):
    node_type: str
    node_name: str
    model_name: str | None = None
    model_version: str | None = None
    model_plugin_id: str | None = None
    parameters_json: dict = Field(default_factory=dict)
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})


class UpdateWorkflowNodeRequest(BaseModel):
    position: dict | None = None
    parameters_json: dict | None = None
    status: str | None = None


class WorkflowLayoutRequest(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


@router.post("/projects/{project_id}/workflow-runs")
def create_workflow_run(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_project_access),
):
    project = catalog.get_project(connection, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    item = catalog.create_draft_workflow_run(connection, project_id)
    return envelope(item)


@router.post("/workflow-runs/{workflow_run_id}/nodes")
def add_workflow_node(
    workflow_run_id: str,
    payload: AddWorkflowNodeRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if run["status"] == "completed":
        raise HTTPException(status_code=409, detail="workflow_run_read_only")

    node = catalog.add_workflow_node(
        connection,
        workflow_run_id,
        node_type=payload.node_type,
        node_name=payload.node_name,
        model_name=payload.model_name,
        model_version=payload.model_version,
        parameters_json=json.dumps(payload.parameters_json),
        position_json=json.dumps(payload.position),
    )
    return envelope(node)


@router.patch("/workflow-runs/{workflow_run_id}/nodes/{node_run_id}")
def patch_workflow_node(
    workflow_run_id: str,
    node_run_id: str,
    payload: UpdateWorkflowNodeRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if run["status"] == "completed":
        raise HTTPException(status_code=409, detail="workflow_run_read_only")

    node = catalog.update_workflow_node(
        connection,
        node_run_id,
        position_json=json.dumps(payload.position) if payload.position else None,
        parameters_json=json.dumps(payload.parameters_json) if payload.parameters_json else None,
        status=payload.status,
    )
    if node is None:
        raise HTTPException(status_code=404, detail="node_not_found")
    return envelope(node)


@router.delete("/workflow-runs/{workflow_run_id}/nodes/{node_run_id}")
def remove_workflow_node(
    workflow_run_id: str,
    node_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if run["status"] == "completed":
        raise HTTPException(status_code=409, detail="workflow_run_read_only")
    if not catalog.delete_workflow_node(connection, node_run_id):
        raise HTTPException(status_code=404, detail="node_not_found")
    return envelope({"deleted": node_run_id})


@router.patch("/workflow-runs/{workflow_run_id}/layout")
def patch_workflow_layout(
    workflow_run_id: str,
    payload: WorkflowLayoutRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if run["status"] == "completed":
        raise HTTPException(status_code=409, detail="workflow_run_read_only")

    layout_json = json.dumps({"nodes": payload.nodes, "edges": payload.edges})
    for node in payload.nodes:
        node_run_id = node.get("node_run_id")
        position = node.get("position")
        if node_run_id and position:
            catalog.update_workflow_node(
                connection,
                node_run_id,
                position_json=json.dumps(position),
            )

    item = catalog.save_workflow_layout(connection, workflow_run_id, layout_json)
    return envelope(item)
