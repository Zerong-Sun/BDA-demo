#!/usr/bin/env python3
"""Register/update model plugin container images and command templates.

Run after init_db to wire model_plugins to their Docker images so the
LocalDockerAdapter can submit real jobs.
"""

from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"

PLUGIN_IMAGES = {
    "RFdiffusion": ("bda/rfdiffusion:1.1.0", "python run.py", {"BDA_GPU": "1"}),
    "ProteinMPNN": ("bda/proteinmpnn:1.0.0", "python run.py", {"BDA_GPU": "1"}),
    "AlphaFold2": ("bda/alphafold2:2.3.0", "python run.py", {"BDA_GPU": "1"}),
    "Rosetta": ("bda/rosetta:2024.09", "python run.py", {}),
}


def register_plugins() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        for model_name, (image, command, env) in PLUGIN_IMAGES.items():
            row = connection.execute(
                "SELECT model_plugin_id FROM model_plugins WHERE model_name = ?",
                (model_name,),
            ).fetchone()
            if row:
                import json

                connection.execute(
                    """
                    UPDATE model_plugins
                    SET container_image = ?, command_template = ?, resource_requirement_json = ?
                    WHERE model_plugin_id = ?
                    """,
                    (
                        image,
                        command,
                        json.dumps({"gpu_count": 1 if env.get("BDA_GPU") else 0, "runtime_env": env}),
                        row["model_plugin_id"],
                    ),
                )
                print(f"Updated {model_name} -> {image}")
            else:
                print(f"Skipped {model_name} (not in registry)")
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    register_plugins()
