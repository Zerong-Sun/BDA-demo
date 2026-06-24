#!/usr/bin/env python3
"""Register/update built-in model plugin manifests.

Run after init_db to refresh model plugin schemas, Docker images, command
templates, resource requirements, and UI-renderable parameter definitions.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DB_PATH = ROOT / "db" / "bda.sqlite3"


def register_plugins() -> None:
    from backend.app.plugins.defaults import default_model_plugins, register_default_model_plugins
    from backend.app.repositories import registry
    from backend.app.repositories.model_catalog import sync_plugin_parameters

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        register_default_model_plugins(connection)
        sync_plugin_parameters(connection, registry.list_model_plugins(connection))
        connection.commit()
        for plugin in default_model_plugins():
            print(f"Registered {plugin['model_name']} -> {plugin['container_image']}")
    finally:
        connection.close()


if __name__ == "__main__":
    register_plugins()
