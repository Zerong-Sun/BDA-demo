from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import decode_row, decode_rows


def sync_plugin_parameters(connection: sqlite3.Connection, plugins: list[dict[str, Any]]) -> int:
    count = 0
    for plugin in plugins:
        plugin_id = plugin["model_plugin_id"]
        fields = (plugin.get("parameter_schema_json") or {}).get("fields") or []
        for field in fields:
            key = str(field.get("key") or "").strip()
            if not key:
                continue
            constraints = {
                name: field[name]
                for name in ("min", "max", "options")
                if name in field
            }
            connection.execute(
                """
                INSERT INTO model_parameter_catalog (
                    parameter_catalog_id, model_plugin_id, parameter_key, label,
                    parameter_type, default_value_json, constraints_json,
                    description, advanced, provenance, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'plugin_schema', 'active')
                ON CONFLICT(model_plugin_id, parameter_key) DO UPDATE SET
                    label=excluded.label,
                    parameter_type=excluded.parameter_type,
                    default_value_json=excluded.default_value_json,
                    constraints_json=excluded.constraints_json,
                    description=excluded.description,
                    advanced=excluded.advanced,
                    status='active',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    f"param_{plugin_id}_{key}".replace(".", "_").replace(":", "_"),
                    plugin_id,
                    key,
                    field.get("label"),
                    field.get("type") or "string",
                    json.dumps(field.get("default")),
                    json.dumps(constraints),
                    field.get("help"),
                    int(bool(field.get("advanced"))),
                ),
            )
            count += 1
    return count


def list_parameters(
    connection: sqlite3.Connection,
    *,
    model_plugin_id: str | None = None,
) -> list[dict[str, Any]]:
    if model_plugin_id:
        rows = connection.execute(
            """
            SELECT * FROM model_parameter_catalog
            WHERE model_plugin_id = ? AND status = 'active'
            ORDER BY advanced, parameter_key
            """,
            (model_plugin_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT * FROM model_parameter_catalog
            WHERE status = 'active'
            ORDER BY model_plugin_id, advanced, parameter_key
            """
        ).fetchall()
    return decode_rows(rows)


def list_script_assets(
    connection: sqlite3.Connection,
    *,
    model_plugin_id: str | None = None,
) -> list[dict[str, Any]]:
    if model_plugin_id:
        rows = connection.execute(
            "SELECT * FROM script_assets WHERE model_plugin_id = ? ORDER BY relative_path",
            (model_plugin_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM script_assets ORDER BY relative_path"
        ).fetchall()
    return decode_rows(rows)


def list_observations(
    connection: sqlite3.Connection,
    *,
    model_plugin_id: str | None = None,
) -> list[dict[str, Any]]:
    if model_plugin_id:
        rows = connection.execute(
            """
            SELECT o.*, s.relative_path
            FROM script_parameter_observations o
            JOIN script_assets s ON s.script_asset_id = o.script_asset_id
            WHERE o.model_plugin_id = ?
            ORDER BY s.relative_path, o.source_line, o.parameter_key
            """,
            (model_plugin_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT o.*, s.relative_path
            FROM script_parameter_observations o
            JOIN script_assets s ON s.script_asset_id = o.script_asset_id
            ORDER BY o.model_plugin_id, s.relative_path, o.source_line
            """
        ).fetchall()
    return decode_rows(rows)


def get_source(connection: sqlite3.Connection, source_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM research_sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    return decode_row(row)
