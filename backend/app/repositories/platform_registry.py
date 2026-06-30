from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows

TABLE_IDS = {
    "datasets": "dataset_id",
    "benchmark_runs": "benchmark_run_id",
    "parameter_presets": "preset_id",
    "workflow_templates": "workflow_template_id",
    "plugin_versions": "plugin_version_id",
}

ORDER_COLUMNS = {
    "created_at DESC",
    "updated_at DESC",
    "name",
    "dataset_type",
    "template_type",
}


def _table(table: str) -> str:
    if table not in TABLE_IDS:
        raise ValueError(f"invalid_registry_table:{table}")
    return table


def _id_column(table: str, id_column: str) -> str:
    expected = TABLE_IDS[_table(table)]
    if id_column != expected:
        raise ValueError(f"invalid_registry_id_column:{id_column}")
    return id_column


def list_table(
    connection: sqlite3.Connection,
    table: str,
    order_by: str = "created_at DESC",
    *,
    limit: int = 100,
) -> list[dict]:
    table = _table(table)
    if order_by not in ORDER_COLUMNS:
        raise ValueError(f"invalid_registry_order:{order_by}")
    rows = connection.execute(f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?", (limit,)).fetchall()
    return decode_rows(rows)


def count_table(connection: sqlite3.Connection, table: str) -> int:
    table = _table(table)
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"]) if row else 0


def create_dataset(
    connection: sqlite3.Connection,
    *,
    dataset_id: str,
    name: str,
    dataset_type: str,
    description: str | None,
    artifact_ids: list[str],
    metadata: dict[str, Any],
    project_id: str | None,
    owner_id: str | None,
    status: str,
) -> dict:
    connection.execute(
        """
        INSERT INTO datasets (
            dataset_id, project_id, name, dataset_type, description,
            artifact_ids_json, metadata_json, owner_id, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset_id,
            project_id,
            name,
            dataset_type,
            description,
            json.dumps(artifact_ids),
            json.dumps(metadata),
            owner_id,
            status,
        ),
    )
    return get_by_id(connection, "datasets", "dataset_id", dataset_id) or {}


def create_benchmark_run(
    connection: sqlite3.Connection,
    *,
    benchmark_run_id: str,
    name: str,
    model_plugin_id: str | None,
    dataset_id: str | None,
    metrics: dict[str, Any],
    context: dict[str, Any],
    status: str,
    created_by: str | None,
) -> dict:
    connection.execute(
        """
        INSERT INTO benchmark_runs (
            benchmark_run_id, model_plugin_id, dataset_id, name,
            metrics_json, context_json, status, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            benchmark_run_id,
            model_plugin_id,
            dataset_id,
            name,
            json.dumps(metrics),
            json.dumps(context),
            status,
            created_by,
        ),
    )
    return get_by_id(connection, "benchmark_runs", "benchmark_run_id", benchmark_run_id) or {}


def create_parameter_preset(
    connection: sqlite3.Connection,
    *,
    preset_id: str,
    name: str,
    parameters: dict[str, Any],
    model_plugin_id: str | None,
    method_plugin_id: str | None,
    description: str | None,
    scope: str,
    status: str,
    created_by: str | None,
) -> dict:
    connection.execute(
        """
        INSERT INTO parameter_presets (
            preset_id, model_plugin_id, method_plugin_id, name, description,
            parameters_json, scope, status, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            preset_id,
            model_plugin_id,
            method_plugin_id,
            name,
            description,
            json.dumps(parameters),
            scope,
            status,
            created_by,
        ),
    )
    return get_by_id(connection, "parameter_presets", "preset_id", preset_id) or {}


def create_workflow_template(
    connection: sqlite3.Connection,
    *,
    workflow_template_id: str,
    name: str,
    template_type: str,
    description: str | None,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    default_parameters: dict[str, Any],
    tags: list[str],
    status: str,
    created_by: str | None,
) -> dict:
    connection.execute(
        """
        INSERT INTO workflow_templates (
            workflow_template_id, name, template_type, description,
            nodes_json, edges_json, default_parameters_json, tags_json, status, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_template_id,
            name,
            template_type,
            description,
            json.dumps(nodes),
            json.dumps(edges),
            json.dumps(default_parameters),
            json.dumps(tags),
            status,
            created_by,
        ),
    )
    return get_by_id(connection, "workflow_templates", "workflow_template_id", workflow_template_id) or {}


def get_by_id(connection: sqlite3.Connection, table: str, id_column: str, item_id: str) -> dict | None:
    table = _table(table)
    id_column = _id_column(table, id_column)
    row = connection.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (item_id,)).fetchone()
    return decode_row(row)


def record_plugin_version(connection: sqlite3.Connection, plugin: dict) -> dict:
    plugin_version_id = f"{plugin['model_plugin_id']}:{plugin['version']}"
    snapshot = {
        "input_schema_json": plugin.get("input_schema_json") or {},
        "output_schema_json": plugin.get("output_schema_json") or {},
        "parameter_schema_json": plugin.get("parameter_schema_json") or {},
        "resource_requirement_json": plugin.get("resource_requirement_json") or {},
    }
    connection.execute(
        """
        INSERT INTO plugin_versions (
            plugin_version_id, model_plugin_id, version, schema_snapshot_json,
            container_image, command_template, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(model_plugin_id, version) DO UPDATE SET
            schema_snapshot_json=excluded.schema_snapshot_json,
            container_image=excluded.container_image,
            command_template=excluded.command_template,
            status=excluded.status
        """,
        (
            plugin_version_id,
            plugin["model_plugin_id"],
            plugin["version"],
            json.dumps(snapshot),
            plugin.get("container_image"),
            plugin.get("command_template"),
            plugin.get("status", "active"),
        ),
    )
    return get_by_id(connection, "plugin_versions", "plugin_version_id", plugin_version_id) or {}
