from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_rows, get_by_id


def create_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_id: str,
    project_id: str | None,
    workflow_run_id: str | None,
    node_run_id: str | None,
    artifact_type: str,
    format: str,
    storage_uri: str,
    display_name: str,
    size_bytes: int,
    checksum: str | None,
    metadata: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO artifacts (
            artifact_id, project_id, workflow_run_id, node_run_id,
            artifact_type, format, storage_uri, display_name,
            size_bytes, checksum, metadata_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            project_id,
            workflow_run_id,
            node_run_id,
            artifact_type,
            format,
            storage_uri,
            display_name,
            size_bytes,
            checksum,
            json.dumps(metadata or {}),
            created_by,
        ),
    )
    return get_artifact(connection, artifact_id) or {}


def get_artifact(connection: sqlite3.Connection, artifact_id: str) -> dict[str, Any] | None:
    return get_by_id(connection, "artifacts", "artifact_id", artifact_id)


def list_project_artifacts(
    connection: sqlite3.Connection,
    project_id: str,
    *,
    artifact_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    filters = ["project_id = ?"]
    params: list[Any] = [project_id]
    if artifact_type:
        filters.append("artifact_type = ?")
        params.append(artifact_type)
    where = " AND ".join(filters)
    total_row = connection.execute(
        f"SELECT COUNT(*) AS total FROM artifacts WHERE {where}",
        params,
    ).fetchone()
    rows = connection.execute(
        f"SELECT * FROM artifacts WHERE {where} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    total = int(total_row["total"]) if total_row else 0
    return decode_rows(rows), total


def list_node_artifacts(connection: sqlite3.Connection, node_run_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM artifacts WHERE node_run_id = ? ORDER BY created_at DESC",
        (node_run_id,),
    ).fetchall()
    return decode_rows(rows)


def list_workflow_artifacts(connection: sqlite3.Connection, workflow_run_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM artifacts WHERE workflow_run_id = ? ORDER BY created_at DESC",
        (workflow_run_id,),
    ).fetchall()
    return decode_rows(rows)
