import json
import sqlite3
from typing import Any

JSON_COLUMNS = {
    "metadata_json",
    "constraints_json",
    "model_route_json",
    "summary_metrics_json",
    "input_files_json",
    "output_files_json",
    "parameters_json",
    "metrics_json",
    "candidate_ids",
    "redesign_constraints",
    "capabilities_json",
    "current_jobs_json",
    "resource_limits_json",
    "input_schema_json",
    "output_schema_json",
    "parameter_schema_json",
    "artifact_schema_json",
    "supported_task_types",
    "supported_file_types",
    "resource_requirement_json",
    "compatible_model_types",
    "compatible_workflow_nodes",
    "default_parameters_json",
    "model_names",
    "allowed_scopes",
    "data_policy",
    "tags_json",
    "related_model_plugins",
    "related_method_plugins",
    "payload_json",
    "input_artifacts",
    "output_artifacts",
}

ALLOWED_TABLES = frozenset({
    "projects",
    "targets",
    "design_tasks",
    "workflow_runs",
    "workflow_node_runs",
    "workflow_edges",
    "candidates",
    "experiment_results",
    "delivery_packages",
    "server_connections",
    "compute_nodes",
    "model_plugins",
    "method_plugins",
    "llm_providers",
    "knowledge_entries",
    "audit_logs",
    "jobs",
    "job_events",
    "artifacts",
    "users",
    "user_sessions",
    "organizations",
    "organization_members",
    "project_members",
})

ALLOWED_ORDER_COLUMNS = frozenset({
    "rowid",
    "created_at",
    "updated_at",
    "project_id",
    "candidate_id",
    "interface_score",
    "plddt",
    "status",
    "artifact_type",
    "display_name",
    "server_name",
    "node_name",
    "model_name",
    "method_name",
    "provider_name",
    "title",
    "category",
    "username",
    "name",
})


class RepositoryError(ValueError):
    pass


def _validate_table(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise RepositoryError(f"invalid_table:{table}")
    return table


def _validate_order_by(order_by: str) -> str:
    # Supports "column" or "column DESC"/"column ASC"
    parts = order_by.strip().split()
    column = parts[0]
    direction = parts[1].upper() if len(parts) > 1 else "ASC"
    if column not in ALLOWED_ORDER_COLUMNS:
        raise RepositoryError(f"invalid_order_by:{order_by}")
    if direction not in ("ASC", "DESC"):
        raise RepositoryError(f"invalid_order_direction:{direction}")
    return f"{column} {direction}" if len(parts) > 1 else column


def _validate_id_column(id_column: str) -> str:
    if not id_column.replace("_", "").isalnum():
        raise RepositoryError(f"invalid_id_column:{id_column}")
    return id_column


def decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in JSON_COLUMNS.intersection(item):
        value = item[key]
        if isinstance(value, str):
            try:
                item[key] = json.loads(value)
            except json.JSONDecodeError:
                pass
    for key, value in list(item.items()):
        if key == "enabled" or key.endswith("_supported"):
            item[key] = bool(value)
    return item


def decode_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [item for row in rows if (item := decode_row(row)) is not None]


def get_by_id(connection: sqlite3.Connection, table: str, id_column: str, item_id: str) -> dict[str, Any] | None:
    table = _validate_table(table)
    id_column = _validate_id_column(id_column)
    row = connection.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (item_id,)).fetchone()
    return decode_row(row)


def list_table(connection: sqlite3.Connection, table: str, order_by: str = "rowid") -> list[dict[str, Any]]:
    table = _validate_table(table)
    order_by = _validate_order_by(order_by)
    rows = connection.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()
    return decode_rows(rows)
