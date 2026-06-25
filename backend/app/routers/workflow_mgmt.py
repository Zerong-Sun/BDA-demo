import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import require_project_access, require_workflow_run_access
from ..db import get_connection
from ..repositories import artifacts as artifact_repo
from ..repositories import catalog, registry
from ..services import job_service
from ..services.workflow_graph import validate_workflow_graph
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
    input_files_json: dict | list | None = None
    status: str | None = None


class WorkflowLayoutRequest(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class WorkflowGraphRequest(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


def _graph_payload(connection: sqlite3.Connection, workflow_run_id: str) -> dict:
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    return {
        "workflow_run": run,
        "nodes": catalog.list_workflow_nodes(connection, workflow_run_id),
        "edges": catalog.list_workflow_edges(connection, workflow_run_id),
        "artifacts": artifact_repo.list_workflow_artifacts(connection, workflow_run_id),
        "jobs": job_service.list_workflow_jobs(connection, workflow_run_id),
    }


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


@router.get("/workflow-runs/{workflow_run_id}/graph")
def get_workflow_graph(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    return envelope(_graph_payload(connection, workflow_run_id))


@router.patch("/workflow-runs/{workflow_run_id}/graph")
def patch_workflow_graph(
    workflow_run_id: str,
    payload: WorkflowGraphRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if run["status"] == "completed":
        raise HTTPException(status_code=409, detail="workflow_run_read_only")
    for node in payload.nodes:
        node_run_id = node.get("node_run_id")
        position = node.get("position")
        if node_run_id and position:
            catalog.update_workflow_node(
                connection,
                node_run_id,
                position_json=json.dumps(position),
            )
    edges = catalog.replace_workflow_edges(connection, workflow_run_id, payload.edges)
    catalog.save_workflow_layout(connection, workflow_run_id, json.dumps({"nodes": payload.nodes, "edges": edges}))
    return envelope(_graph_payload(connection, workflow_run_id))


@router.post("/workflow-runs/{workflow_run_id}/validate")
def validate_workflow(
    workflow_run_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_workflow_run_access),
):
    run = catalog.get_workflow_run(connection, workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    edges = catalog.list_workflow_edges(connection, workflow_run_id)
    plugins = registry.list_model_plugins(connection)
    return envelope(validate_workflow_graph(nodes, edges, plugins))


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
    existing_node = catalog.get_workflow_node(connection, node_run_id)
    if existing_node is None or existing_node.get("workflow_run_id") != workflow_run_id:
        raise HTTPException(status_code=404, detail="node_not_found")
    if payload.status is not None:
        controlled_manual_types = {
            "research_review",
            "structure_preparation",
            "review_gate",
        }
        parameters = existing_node.get("parameters_json") or {}
        if (
            parameters.get("requires_user_review")
            or existing_node.get("node_type") in controlled_manual_types
            or existing_node.get("status") == "waiting_external_result"
        ):
            raise HTTPException(
                status_code=409,
                detail="controlled_node_requires_specialized_transition",
            )
    if payload.input_files_json is not None:
        project_id = catalog.get_workflow_run_project_id(connection, workflow_run_id)
        refs: list[str] = []
        values = (
            payload.input_files_json.values()
            if isinstance(payload.input_files_json, dict)
            else payload.input_files_json
        )
        for value in values:
            entries = value if isinstance(value, list) else [value]
            for entry in entries:
                if isinstance(entry, str):
                    refs.append(entry)
                elif isinstance(entry, dict) and entry.get("artifact_id"):
                    refs.append(str(entry["artifact_id"]))
        for artifact_id in refs:
            artifact = artifact_repo.get_artifact(connection, artifact_id)
            if artifact is None:
                raise HTTPException(status_code=400, detail=f"artifact_not_found:{artifact_id}")
            if artifact.get("project_id") != project_id:
                raise HTTPException(status_code=403, detail="artifact_project_mismatch")

    node = catalog.update_workflow_node(
        connection,
        node_run_id,
        position_json=json.dumps(payload.position) if payload.position else None,
        parameters_json=json.dumps(payload.parameters_json) if payload.parameters_json is not None else None,
        input_files_json=json.dumps(payload.input_files_json) if payload.input_files_json is not None else None,
        status=payload.status,
    )
    if node is None:
        raise HTTPException(status_code=404, detail="node_not_found")
    if payload.parameters_json is not None and existing_node.get("model_name"):
        plan_row = connection.execute(
            """
            SELECT workflow_plan_id, nodes_json FROM workflow_plans
            WHERE materialized_workflow_run_id = ?
            """,
            (workflow_run_id,),
        ).fetchone()
        plan_node_key = None
        if plan_row:
            planned_nodes = json.loads(plan_row["nodes_json"] or "[]")
            matched = next(
                (
                    planned
                    for planned in planned_nodes
                    if planned.get("name") == existing_node.get("node_name")
                    and planned.get("model_name") == existing_node.get("model_name")
                ),
                None,
            )
            plan_node_key = (matched or {}).get("key")
        recommendation_rows = connection.execute(
            """
            SELECT r.parameter_recommendation_id, r.parameter_key, r.recommended_value_json
            FROM parameter_recommendations r
            WHERE r.workflow_plan_id = ? AND r.node_key = ?
            """,
            (plan_row["workflow_plan_id"], plan_node_key),
        ).fetchall() if plan_row and plan_node_key else []
        for recommendation in recommendation_rows:
            recommended = json.loads(recommendation["recommended_value_json"])
            current = payload.parameters_json.get(recommendation["parameter_key"])
            connection.execute(
                """
                UPDATE parameter_recommendations
                SET user_modified = ?, updated_at = CURRENT_TIMESTAMP
                WHERE parameter_recommendation_id = ?
                """,
                (int(current != recommended), recommendation["parameter_recommendation_id"]),
            )
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

    catalog.replace_workflow_edges(connection, workflow_run_id, payload.edges)
    item = catalog.save_workflow_layout(connection, workflow_run_id, layout_json)
    return envelope(item)
