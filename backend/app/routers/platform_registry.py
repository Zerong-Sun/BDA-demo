import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user
from ..db import get_connection
from ..repositories import platform_registry, registry
from ..utils.response import envelope

router = APIRouter(prefix="/platform-registry")


class CreateDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    dataset_type: str = Field(default="custom", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    artifact_ids_json: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)
    project_id: str | None = Field(default=None, max_length=120)
    status: str = Field(default="active", pattern="^(active|draft|archived)$")


class CreateBenchmarkRunRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    model_plugin_id: str | None = Field(default=None, max_length=120)
    dataset_id: str | None = Field(default=None, max_length=120)
    metrics_json: dict = Field(default_factory=dict)
    context_json: dict = Field(default_factory=dict)
    status: str = Field(default="planned", pattern="^(planned|running|completed|failed|archived)$")


class CreateParameterPresetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parameters_json: dict = Field(default_factory=dict)
    model_plugin_id: str | None = Field(default=None, max_length=120)
    method_plugin_id: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    scope: str = Field(default="model", pattern="^(model|method|workflow|project)$")
    status: str = Field(default="active", pattern="^(active|draft|archived)$")


class CreateWorkflowTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    template_type: str = Field(default="custom", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    nodes_json: list[dict] = Field(default_factory=list)
    edges_json: list[dict] = Field(default_factory=list)
    default_parameters_json: dict = Field(default_factory=dict)
    tags_json: list[str] = Field(default_factory=list)
    status: str = Field(default="active", pattern="^(active|draft|archived)$")


def _write_allowed(user: dict) -> None:
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")


def _list_payload(connection: sqlite3.Connection, table: str) -> dict:
    return {
        "items": platform_registry.list_table(connection, table),
        "total": platform_registry.count_table(connection, table),
    }


@router.get("/datasets")
def list_datasets(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return envelope(_list_payload(connection, "datasets"))


@router.post("/datasets")
def create_dataset(
    payload: CreateDatasetRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _write_allowed(user)
    item = platform_registry.create_dataset(
        connection,
        dataset_id=f"dataset_{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        dataset_type=payload.dataset_type.strip(),
        description=payload.description,
        artifact_ids=payload.artifact_ids_json,
        metadata=payload.metadata_json,
        project_id=payload.project_id,
        owner_id=user.get("user_id"),
        status=payload.status,
    )
    return envelope(item)


@router.get("/benchmark-runs")
def list_benchmark_runs(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return envelope(_list_payload(connection, "benchmark_runs"))


@router.post("/benchmark-runs")
def create_benchmark_run(
    payload: CreateBenchmarkRunRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _write_allowed(user)
    if payload.model_plugin_id and registry.get_model_plugin(connection, payload.model_plugin_id) is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    if payload.dataset_id and platform_registry.get_by_id(connection, "datasets", "dataset_id", payload.dataset_id) is None:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    item = platform_registry.create_benchmark_run(
        connection,
        benchmark_run_id=f"benchmark_{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        model_plugin_id=payload.model_plugin_id,
        dataset_id=payload.dataset_id,
        metrics=payload.metrics_json,
        context=payload.context_json,
        status=payload.status,
        created_by=user.get("user_id"),
    )
    return envelope(item)


@router.get("/parameter-presets")
def list_parameter_presets(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return envelope(_list_payload(connection, "parameter_presets"))


@router.post("/parameter-presets")
def create_parameter_preset(
    payload: CreateParameterPresetRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _write_allowed(user)
    if payload.model_plugin_id and registry.get_model_plugin(connection, payload.model_plugin_id) is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    if payload.method_plugin_id and registry.get_method_plugin(connection, payload.method_plugin_id) is None:
        raise HTTPException(status_code=404, detail="method_plugin_not_found")
    item = platform_registry.create_parameter_preset(
        connection,
        preset_id=f"preset_{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        parameters=payload.parameters_json,
        model_plugin_id=payload.model_plugin_id,
        method_plugin_id=payload.method_plugin_id,
        description=payload.description,
        scope=payload.scope,
        status=payload.status,
        created_by=user.get("user_id"),
    )
    return envelope(item)


@router.get("/workflow-templates")
def list_workflow_templates(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return envelope(_list_payload(connection, "workflow_templates"))


@router.post("/workflow-templates")
def create_workflow_template(
    payload: CreateWorkflowTemplateRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _write_allowed(user)
    item = platform_registry.create_workflow_template(
        connection,
        workflow_template_id=f"template_{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        template_type=payload.template_type.strip(),
        description=payload.description,
        nodes=payload.nodes_json,
        edges=payload.edges_json,
        default_parameters=payload.default_parameters_json,
        tags=payload.tags_json,
        status=payload.status,
        created_by=user.get("user_id"),
    )
    return envelope(item)


@router.get("/plugin-versions")
def list_plugin_versions(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return envelope(_list_payload(connection, "plugin_versions"))
