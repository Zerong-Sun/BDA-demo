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
