from __future__ import annotations

import sqlite3
from typing import Any

from ..services.script_importer import consistency_report


def model_parameter_consistency(
    connection: sqlite3.Connection,
    model_plugin_id: str,
) -> dict[str, Any]:
    report = consistency_report(connection, model_plugin_id=model_plugin_id)
    models = report.get("models") or []
    return models[0] if models else {
        "model_plugin_id": model_plugin_id,
        "matched": [],
        "script_only": [],
        "catalog_only": [],
    }
