import sqlite3
from typing import Any

from .base import decode_rows, get_by_id, list_table


def _paginate_table(
    connection: sqlite3.Connection,
    table: str,
    order_by: str,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    count_row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    total = int(count_row["total"]) if count_row else 0
    rows = connection.execute(
        f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return decode_rows(rows), total


def list_servers(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "server_connections", "server_name")


def list_servers_paginated(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    return _paginate_table(connection, "server_connections", "server_name", limit=limit, offset=offset)


def get_server(connection: sqlite3.Connection, server_id: str) -> dict | None:
    return get_by_id(connection, "server_connections", "server_id", server_id)


def create_server(
    connection: sqlite3.Connection,
    *,
    server_id: str,
    server_name: str,
    server_type: str,
    base_url: str | None = None,
    auth_type: str = "none",
    credential_ref: str | None = None,
    network_status: str = "unknown",
    health_check_endpoint: str | None = None,
    capabilities: dict[str, Any] | None = None,
    owner_id: str | None = None,
    enabled: bool = True,
) -> dict:
    import json

    connection.execute(
        """
        INSERT INTO server_connections (
            server_id, server_name, server_type, base_url, auth_type, credential_ref,
            network_status, health_check_endpoint, capabilities_json, owner_id, enabled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            server_id,
            server_name,
            server_type,
            base_url,
            auth_type,
            credential_ref,
            network_status,
            health_check_endpoint,
            json.dumps(capabilities or {}),
            owner_id,
            1 if enabled else 0,
        ),
    )
    return get_server(connection, server_id) or {}


def update_server(
    connection: sqlite3.Connection,
    server_id: str,
    *,
    server_name: str | None = None,
    server_type: str | None = None,
    base_url: str | None = None,
    auth_type: str | None = None,
    credential_ref: str | None = None,
    network_status: str | None = None,
    health_check_endpoint: str | None = None,
    capabilities: dict[str, Any] | None = None,
    enabled: bool | None = None,
    last_health_check_at: str | None = None,
) -> dict | None:
    import json

    updates: list[str] = []
    values: list[Any] = []
    fields: dict[str, Any] = {
        "server_name": server_name,
        "server_type": server_type,
        "base_url": base_url,
        "auth_type": auth_type,
        "credential_ref": credential_ref,
        "network_status": network_status,
        "health_check_endpoint": health_check_endpoint,
        "last_health_check_at": last_health_check_at,
    }
    for column, value in fields.items():
        if value is not None:
            updates.append(f"{column} = ?")
            values.append(value)
    if capabilities is not None:
        updates.append("capabilities_json = ?")
        values.append(json.dumps(capabilities))
    if enabled is not None:
        updates.append("enabled = ?")
        values.append(1 if enabled else 0)
    if updates:
        values.append(server_id)
        connection.execute(
            f"UPDATE server_connections SET {', '.join(updates)} WHERE server_id = ?",
            values,
        )
    return get_server(connection, server_id)


def list_compute_nodes(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "compute_nodes", "node_name")


def list_compute_nodes_paginated(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    return _paginate_table(connection, "compute_nodes", "node_name", limit=limit, offset=offset)


def get_compute_node(connection: sqlite3.Connection, compute_node_id: str) -> dict | None:
    return get_by_id(connection, "compute_nodes", "compute_node_id", compute_node_id)


def update_compute_node_status(
    connection: sqlite3.Connection,
    compute_node_id: str,
    *,
    status: str,
) -> dict | None:
    connection.execute(
        "UPDATE compute_nodes SET status = ?, last_seen_at = CURRENT_TIMESTAMP WHERE compute_node_id = ?",
        (status, compute_node_id),
    )
    return get_compute_node(connection, compute_node_id)


def list_model_plugins(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "model_plugins", "model_name")


def list_model_plugins_paginated(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    return _paginate_table(connection, "model_plugins", "model_name", limit=limit, offset=offset)


def get_model_plugin(connection: sqlite3.Connection, model_plugin_id: str) -> dict | None:
    return get_by_id(connection, "model_plugins", "model_plugin_id", model_plugin_id)


def create_model_plugin(
    connection: sqlite3.Connection,
    *,
    model_plugin_id: str,
    model_name: str,
    model_type: str,
    provider: str,
    version: str,
    description: str | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    parameter_schema: dict[str, Any] | None = None,
    artifact_schema: dict[str, Any] | None = None,
    supported_task_types: list[str] | None = None,
    supported_file_types: list[str] | None = None,
    resource_requirement: dict[str, Any] | None = None,
    default_compute_node_id: str | None = None,
    container_image: str | None = None,
    command_template: str | None = None,
    api_endpoint: str | None = None,
    license: str | None = None,
    citation: str | None = None,
    status: str = "experimental",
) -> dict:
    import json

    connection.execute(
        """
        INSERT INTO model_plugins (
            model_plugin_id, model_name, model_type, provider, version, description,
            input_schema_json, output_schema_json, parameter_schema_json,
            artifact_schema_json, supported_task_types, supported_file_types,
            resource_requirement_json, default_compute_node_id, container_image,
            command_template, api_endpoint, license, citation, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            model_plugin_id,
            model_name,
            model_type,
            provider,
            version,
            description,
            json.dumps(input_schema or {}),
            json.dumps(output_schema or {}),
            json.dumps(parameter_schema or {}),
            json.dumps(artifact_schema or {}),
            json.dumps(supported_task_types or []),
            json.dumps(supported_file_types or []),
            json.dumps(resource_requirement or {}),
            default_compute_node_id,
            container_image,
            command_template,
            api_endpoint,
            license,
            citation,
            status,
        ),
    )
    return get_model_plugin(connection, model_plugin_id) or {}


def list_method_plugins(connection: sqlite3.Connection) -> list[dict]:
    return list_table(connection, "method_plugins", "method_name")


def list_method_plugins_paginated(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    return _paginate_table(connection, "method_plugins", "method_name", limit=limit, offset=offset)


def get_method_plugin(connection: sqlite3.Connection, method_plugin_id: str) -> dict | None:
    return get_by_id(connection, "method_plugins", "method_plugin_id", method_plugin_id)


def create_method_plugin(
    connection: sqlite3.Connection,
    *,
    method_plugin_id: str,
    method_name: str,
    method_type: str,
    description: str | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    parameter_schema: dict[str, Any] | None = None,
    compatible_model_types: list[str] | None = None,
    compatible_workflow_nodes: list[str] | None = None,
    default_parameters: dict[str, Any] | None = None,
    version: str = "custom-1.0",
    owner_id: str | None = None,
    status: str = "active",
) -> dict:
    import json

    connection.execute(
        """
        INSERT INTO method_plugins (
            method_plugin_id, method_name, method_type, description,
            input_schema_json, output_schema_json, parameter_schema_json,
            compatible_model_types, compatible_workflow_nodes,
            default_parameters_json, version, owner_id, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            method_plugin_id,
            method_name,
            method_type,
            description,
            json.dumps(input_schema or {}),
            json.dumps(output_schema or {}),
            json.dumps(parameter_schema or {}),
            json.dumps(compatible_model_types or []),
            json.dumps(compatible_workflow_nodes or []),
            json.dumps(default_parameters or {}),
            version,
            owner_id,
            status,
        ),
    )
    return get_method_plugin(connection, method_plugin_id) or {}
