#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.script_importer import import_script_tree  # noqa: E402


def main() -> None:
    from backend.scripts.init_db import DB_PATH, SCHEMA

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO_ROOT / "qm-scripts"
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA.read_text())
        result = import_script_tree(connection, root, repository_root=REPO_ROOT)
        connection.commit()
    finally:
        connection.close()
    print(
        f"Imported {result['scripts_imported']} scripts, "
        f"{result['parameter_observations']} parameter observations, "
        f"{result['parse_warnings']} warnings."
    )


if __name__ == "__main__":
    main()
