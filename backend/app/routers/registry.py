import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_connection
from ..repositories import registry
from ..utils.response import envelope

router = APIRouter()


@router.get("/servers")
def servers(connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(registry.list_servers(connection))


@router.get("/servers/{server_id}")
def server(server_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_server(connection, server_id)
    if item is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    return envelope(item)


@router.post("/servers/{server_id}/health-check")
def server_health_check(server_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_server(connection, server_id)
    if item is None:
        raise HTTPException(status_code=404, detail="server_not_found")
    return envelope({"server_id": server_id, "status": item["network_status"], "demo_mode": True})


@router.get("/compute-nodes")
def compute_nodes(connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(registry.list_compute_nodes(connection))


@router.get("/compute-nodes/{compute_node_id}")
def compute_node(compute_node_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    return envelope(item)


@router.post("/compute-nodes/{compute_node_id}/health-check")
def compute_node_health_check(compute_node_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_compute_node(connection, compute_node_id)
    if item is None:
        raise HTTPException(status_code=404, detail="compute_node_not_found")
    return envelope({
        "compute_node_id": compute_node_id,
        "status": item["status"],
        "accepting_jobs": item["status"] == "available",
    })


@router.get("/model-plugins")
def model_plugins(connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(registry.list_model_plugins(connection))


@router.get("/model-plugins/{model_plugin_id}")
def model_plugin(model_plugin_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_model_plugin(connection, model_plugin_id)
    if item is None:
        raise HTTPException(status_code=404, detail="model_plugin_not_found")
    return envelope(item)


@router.post("/model-plugins/{model_plugin_id}/validate-schema")
def validate_model_plugin(model_plugin_id: str, connection: sqlite3.Connection = Depends(get_connection)):
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
def method_plugins(connection: sqlite3.Connection = Depends(get_connection)):
    return envelope(registry.list_method_plugins(connection))


@router.get("/method-plugins/{method_plugin_id}")
def method_plugin(method_plugin_id: str, connection: sqlite3.Connection = Depends(get_connection)):
    item = registry.get_method_plugin(connection, method_plugin_id)
    if item is None:
        raise HTTPException(status_code=404, detail="method_plugin_not_found")
    return envelope(item)


@router.get("/llm-providers")
def llm_providers(connection: sqlite3.Connection = Depends(get_connection)):
    from ..repositories.base import decode_rows

    rows = connection.execute("SELECT * FROM llm_providers").fetchall()
    return envelope(decode_rows(rows))


@router.post("/llm-providers/{llm_provider_id}/test")
def test_llm_provider(llm_provider_id: str, connection: sqlite3.Connection = Depends(get_connection)):
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
