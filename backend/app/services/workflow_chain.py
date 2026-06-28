from __future__ import annotations

import json
import sqlite3

from ..repositories import catalog

WORKFLOW_CHAIN = [
    ("backbone_generation", "RFdiffusion", "bda/rfdiffusion:1.1.0"),
    ("sequence_design", "ProteinMPNN", "bda/proteinmpnn:1.0.0"),
    ("structure_prediction", "AlphaFold2", "bda/alphafold2:2.3.0"),
    ("interface_scoring", "Rosetta", "bda/rosetta:2024.09"),
]


def chain_node_outputs(connection: sqlite3.Connection, workflow_run_id: str) -> None:
    """Propagate output_artifacts from completed nodes to downstream node inputs."""
    nodes = catalog.list_workflow_nodes(connection, workflow_run_id)
    completed = {n["node_run_id"]: n for n in nodes if n.get("status") == "completed"}

    for i, node in enumerate(nodes):
        if i == 0 or node["node_run_id"] in completed:
            continue
        prev = nodes[i - 1]
        prev_outputs = prev.get("output_files_json") or []
        if prev_outputs and prev.get("status") == "completed":
            catalog.update_workflow_node(
                connection,
                node["node_run_id"],
                parameters_json=json.dumps({
                    **(node.get("parameters_json") or {}),
                    "inherited_from": prev["node_run_id"],
                    "input_files": prev_outputs,
                }),
            )


def get_plugin_for_model(connection: sqlite3.Connection, model_name: str) -> dict | None:
    from ..repositories import registry

    plugins = registry.list_model_plugins(connection)
    return next((p for p in plugins if p.get("model_name") == model_name), None)
