import re
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, require_role
from ..db import get_connection
from ..repositories import model_catalog, platform_registry, registry
from ..utils.response import envelope

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[3]


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


class CreateModelPluginRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=120)
    model_type: str = Field(min_length=1, max_length=80)
    provider: str = Field(default="custom", min_length=1, max_length=120)
    version: str = Field(default="custom-1.0", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    input_schema_json: dict = Field(default_factory=dict)
    output_schema_json: dict = Field(default_factory=dict)
    parameter_schema_json: dict = Field(default_factory=dict)
    artifact_schema_json: dict = Field(default_factory=dict)
    supported_task_types: list[str] = Field(default_factory=list)
    supported_file_types: list[str] = Field(default_factory=list)
    resource_requirement_json: dict = Field(default_factory=dict)
    default_compute_node_id: str | None = Field(default=None, max_length=120)
    container_image: str | None = Field(default=None, max_length=240)
    command_template: str | None = Field(default=None, max_length=1000)
    api_endpoint: str | None = Field(default=None, max_length=500)
    license: str | None = Field(default=None, max_length=240)
    citation: str | None = Field(default=None, max_length=500)
    status: str = Field(default="experimental", pattern="^(active|experimental|disabled|restricted)$")


class CreateServerRequest(BaseModel):
    server_name: str = Field(min_length=1, max_length=120)
    server_type: str = Field(default="http_worker", min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=500)
    auth_type: str = Field(default="none", pattern="^(none|token|basic|ssh_key|managed_secret)$")
    credential_ref: str | None = Field(default=None, max_length=240)
    health_check_endpoint: str | None = Field(default="/health", max_length=240)
    capabilities_json: dict = Field(default_factory=dict)
    enabled: bool = True


class UpdateServerRequest(BaseModel):
    server_name: str | None = Field(default=None, min_length=1, max_length=120)
    server_type: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=500)
    auth_type: str | None = Field(default=None, pattern="^(none|token|basic|ssh_key|managed_secret)$")
    credential_ref: str | None = Field(default=None, max_length=240)
    health_check_endpoint: str | None = Field(default=None, max_length=240)
    capabilities_json: dict | None = None
    enabled: bool | None = None


def _test_server_connection(item: dict) -> dict:
    base_url = (item.get("base_url") or "").rstrip("/")
    endpoint = item.get("health_check_endpoint") or "/health"
    if not base_url:
        return {"connected": False, "status": "unavailable", "reason": "missing_base_url"}
    url = f"{base_url}{endpoint if endpoint.startswith('/') else f'/{endpoint}'}"
    request = Request(url, headers={"User-Agent": "BDA-health-check/1.0"})
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310 - admin-configured health check URL
            ok = 200 <= response.status < 500
            return {
                "connected": ok,
                "status": "available" if ok else "unavailable",
                "http_status": response.status,
                "url": url,
            }
    except (TimeoutError, URLError, OSError) as exc:
        return {"connected": False, "status": "unavailable", "reason": str(exc), "url": url}


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


@router.post("/servers")
def create_server(
    payload: CreateServerRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(require_role("admin")),
):
    server_name = payload.server_name.strip()
    server_type = payload.server_type.strip()
    if not server_name or not server_type:
        raise HTTPException(status_code=422, detail="server_name_and_type_required")
    item = registry.create_server(
        connection,
        server_id=f"server_{uuid.uuid4().hex[:12]}",
        server_name=server_name,
        server_type=server_type,
        base_url=payload.base_url.strip() if payload.base_url else None,
        auth_type=payload.auth_type,
        credential_ref=payload.credential_ref,
        network_status="unknown",
        health_check_endpoint=payload.health_check_endpoint,
        capabilities=payload.capabilities_json,
        owner_id=user.get("user_id"),
        enabled=payload.enabled,
    )
    return envelope(item)


@router.patch("/servers/{server_id}")
def update_server(
    server_id: str,
    payload: UpdateServerRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    if registry.get_server(connection, server_id) is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    item = registry.update_server(
        connection,
        server_id,
        server_name=payload.server_name.strip() if payload.server_name else None,
        server_type=payload.server_type.strip() if payload.server_type else None,
        base_url=payload.base_url.strip() if payload.base_url else None,
        auth_type=payload.auth_type,
        credential_ref=payload.credential_ref,
        health_check_endpoint=payload.health_check_endpoint,
        capabilities=payload.capabilities_json,
        enabled=payload.enabled,
    )
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


@router.post("/servers/{server_id}/test-connection")
def test_server_connection(
    server_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = registry.get_server(connection, server_id)
    if item is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    result = _test_server_connection(item)
    updated = registry.update_server(
        connection,
        server_id,
        network_status=result["status"],
        last_health_check_at=datetime.now(UTC).isoformat(),
    )
    return envelope({"server": updated, **result})


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


@router.get("/compute-nodes/{compute_node_id}/queue")
def compute_node_queue(
    compute_node_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    from ..repositories.base import decode_rows

    rows = connection.execute(
        """
        SELECT job_id, workflow_run_id, node_run_id, status, plugin_id, external_id, created_at, started_at, finished_at
        FROM jobs
        WHERE compute_node_id = ?
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (compute_node_id,),
    ).fetchall()
    jobs = decode_rows(rows)
    active = [job for job in jobs if job.get("status") in {"queued", "staging", "running", "collecting_outputs"}]
    return envelope({
        "compute_node": item,
        "jobs": jobs,
        "active_jobs": active,
        "accepting_jobs": item.get("status") == "available",
    })


@router.post("/compute-nodes/{compute_node_id}/drain")
def drain_compute_node(
    compute_node_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    updated = registry.update_compute_node_status(connection, compute_node_id, status="draining")
    return envelope({
        "compute_node": updated,
        "accepting_jobs": False,
        "message": "Node marked draining; existing jobs are left untouched.",
    })


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


@router.post("/model-plugins")
def create_model_plugin(
    payload: CreateModelPluginRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    model_name = payload.model_name.strip()
    model_type = payload.model_type.strip()
    provider = payload.provider.strip()
    if not model_name or not model_type or not provider:
        raise HTTPException(status_code=422, detail="model_name_type_provider_required")
    default_compute_node_id = payload.default_compute_node_id.strip() if payload.default_compute_node_id else None
    if default_compute_node_id and registry.get_compute_node(connection, default_compute_node_id) is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    item = registry.create_model_plugin(
        connection,
        model_plugin_id=f"plugin_{uuid.uuid4().hex[:12]}",
        model_name=model_name,
        model_type=model_type,
        provider=provider,
        version=payload.version.strip(),
        description=payload.description,
        input_schema=payload.input_schema_json,
        output_schema=payload.output_schema_json,
        parameter_schema=payload.parameter_schema_json,
        artifact_schema=payload.artifact_schema_json,
        supported_task_types=payload.supported_task_types,
        supported_file_types=payload.supported_file_types,
        resource_requirement=payload.resource_requirement_json,
        default_compute_node_id=default_compute_node_id,
        container_image=payload.container_image,
        command_template=payload.command_template,
        api_endpoint=payload.api_endpoint,
        license=payload.license,
        citation=payload.citation,
        status=payload.status,
    )
    platform_registry.record_plugin_version(connection, item)
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


@router.get("/model-parameter-catalog")
def model_parameter_catalog(
    model_plugin_id: str | None = Query(default=None, max_length=120),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    if model_plugin_id and registry.get_model_plugin(connection, model_plugin_id) is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    items = model_catalog.list_parameters(
        connection,
        model_plugin_id=model_plugin_id,
    )
    return envelope({"items": items, "total": len(items), "model_plugin_id": model_plugin_id})


@router.get("/script-assets")
def script_assets(
    model_plugin_id: str | None = Query(default=None, max_length=120),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items = model_catalog.list_script_assets(
        connection,
        model_plugin_id=model_plugin_id,
    )
    return envelope({"items": items, "total": len(items), "model_plugin_id": model_plugin_id})


@router.post("/script-assets/upload")
async def upload_script_asset(
    model_plugin_id: str | None = Form(default=None),
    relative_path: str | None = Form(default=None),
    file: UploadFile = File(...),
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=422, detail="filename_required")
    suffix = Path(filename).suffix.lower()
    from ..services.script_importer import SUPPORTED_SUFFIXES, import_script_file

    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail="unsupported_script_type")
    if model_plugin_id and registry.get_model_plugin(connection, model_plugin_id) is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")

    requested_path = (relative_path or filename).strip().replace("\\", "/")
    if requested_path.startswith("/") or ".." in Path(requested_path).parts:
        raise HTTPException(status_code=422, detail="invalid_relative_path")
    if not re.fullmatch(r"[A-Za-z0-9._/\-]+", requested_path):
        raise HTTPException(status_code=422, detail="invalid_relative_path")
    if not Path(requested_path).suffix:
        requested_path = f"{requested_path.rstrip('/')}/{filename}"
    upload_path = f"uploaded-scripts/{requested_path}"

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty_script")
    with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(raw)
        handle.flush()
        item = import_script_file(
            connection,
            Path(handle.name),
            relative_path=upload_path,
            model_plugin_id=model_plugin_id,
            metadata={
                "uploaded_by": user.get("user_id"),
                "original_filename": filename,
                "upload_size_bytes": len(raw),
            },
        )
    return envelope({"success": True, "item": item})


@router.post("/model-parameter-catalog/import-qm-scripts")
def import_qm_scripts(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    from ..services.script_importer import import_script_tree

    root = REPO_ROOT / "qm-scripts"
    if not root.exists():
        raise HTTPException(status_code=404, detail="qm_scripts_not_found")
    result = import_script_tree(connection, root, repository_root=REPO_ROOT)
    return envelope(result)


@router.get("/model-parameter-catalog/consistency")
def model_parameter_consistency(
    model_plugin_id: str | None = Query(default=None, max_length=120),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    from ..services.script_importer import consistency_report

    return envelope(consistency_report(connection, model_plugin_id=model_plugin_id))


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
