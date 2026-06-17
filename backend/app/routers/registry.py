import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, require_role
from ..db import get_connection
from ..repositories import registry
from ..utils.response import envelope

router = APIRouter()


class CreateMethodPluginRequest(BaseModel):
    method_name: str = Field(min_length=1, max_length=120)
    method_type: str = Field(default="custom", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    input_schema_json: dict = Field(default_factory=dict)
    output_schema_json: dict = Field(default_factory=dict)
    parameter_schema_json: dict = Field(default_factory=dict)
    compatible_model_types: list[str] = Field(default_factory=list)
    compatible_workflow_nodes: list[str] = Field(default_factory=list)
    default_parameters_json: dict = Field(default_factory=dict)
    version: str = Field(default="custom-1.0", min_length=1, max_length=80)
    status: str = Field(default="active", pattern="^(active|experimental|disabled)$")


@router.get("/servers")
def servers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items, total = registry.list_servers_paginated(connection, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/servers/{server_id}")
def server(
    server_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = registry.get_server(connection, server_id)
    if item is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    return envelope(item)


@router.post("/servers/{server_id}/health-check")
def server_health_check(
    server_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = registry.get_server(connection, server_id)
    if item is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    return envelope({"server_id": server_id, "status": item["network_status"], "demo_mode": True})


@router.get("/compute-nodes")
def compute_nodes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items, total = registry.list_compute_nodes_paginated(connection, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/compute-nodes/{compute_node_id}")
def compute_node(
    compute_node_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    return envelope(item)


@router.post("/compute-nodes/{compute_node_id}/health-check")
def compute_node_health_check(
    compute_node_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    return envelope({
        "compute_node_id": compute_node_id,
        "status": item["status"],
        "accepting_jobs": item["status"] == "available",
    })


@router.get("/model-plugins")
def model_plugins(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items, total = registry.list_model_plugins_paginated(connection, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/model-plugins/{model_plugin_id}")
def model_plugin(
    model_plugin_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = registry.get_model_plugin(connection, model_plugin_id)
    if item is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    return envelope(item)


@router.post("/model-plugins/{model_plugin_id}/validate-schema")
def validate_model_plugin(
    model_plugin_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = registry.get_model_plugin(connection, model_plugin_id)
    if item is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    required = ["input_schema_json", "output_schema_json", "parameter_schema_json", "resource_requirement_json"]
    return envelope({
        "model_plugin_id": model_plugin_id,
        "valid": all(item.get(key) is not None for key in required),
        "status": item["status"],
    })


@router.get("/method-plugins")
def method_plugins(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items, total = registry.list_method_plugins_paginated(connection, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/method-plugins/{method_plugin_id}")
def method_plugin(
    method_plugin_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = registry.get_method_plugin(connection, method_plugin_id)
    if item is None:
        raise HTTPException(status_code=404, detail="method_plugin_not_found")
    return envelope(item)


@router.post("/method-plugins")
def create_method_plugin(
    payload: CreateMethodPluginRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    method_name = payload.method_name.strip()
    method_type = payload.method_type.strip()
    if not method_name or not method_type:
        raise HTTPException(status_code=422, detail="method_name_and_type_required")
    item = registry.create_method_plugin(
        connection,
        method_plugin_id=f"method_{uuid.uuid4().hex[:12]}",
        method_name=method_name,
        method_type=method_type,
        description=payload.description,
        input_schema=payload.input_schema_json,
        output_schema=payload.output_schema_json,
        parameter_schema=payload.parameter_schema_json,
        compatible_model_types=payload.compatible_model_types,
        compatible_workflow_nodes=payload.compatible_workflow_nodes,
        default_parameters=payload.default_parameters_json,
        version=payload.version,
        owner_id=user.get("user_id"),
        status=payload.status,
    )
    return envelope(item)


@router.get("/llm-providers")
def llm_providers(
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    from ..repositories.base import decode_rows

    rows = connection.execute("SELECT * FROM llm_providers").fetchall()
    return envelope(decode_rows(rows))


@router.post("/llm-providers/{llm_provider_id}/test")
def test_llm_provider(
    llm_provider_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    from ..settings import get_settings

    settings = get_settings()
    if not settings.llm_api_key:
        return envelope({"llm_provider_id": llm_provider_id, "connected": False, "reason": "no_api_key"})
    try:
        from ..copilot.provider import get_llm_provider

        provider = get_llm_provider()
        resp = provider.chat([{"role": "user", "content": "ping"}])
        return envelope({"llm_provider_id": llm_provider_id, "connected": True, "sample": resp.content[:80]})
    except Exception as exc:
        return envelope({"llm_provider_id": llm_provider_id, "connected": False, "reason": str(exc)})
