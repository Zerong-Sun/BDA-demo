from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..repositories import catalog, knowledge, registry

PLUGIN_BY_ID = {
    "rfdiffusion": ("plugin_rfdiffusion", "RFdiffusion", "backbone_generation"),
    "proteinmpnn": ("plugin_proteinmpnn", "ProteinMPNN", "sequence_generation"),
    "alphafold2": ("plugin_alphafold2", "AlphaFold2", "fold_prediction"),
    "alphafold3": ("plugin_alphafold3", "AlphaFold 3", "fold_prediction"),
    "boltz": ("plugin_boltz", "Boltz", "fold_prediction"),
    "chai1": ("plugin_chai1", "Chai-1", "fold_prediction"),
    "rosetta": ("plugin_rosetta", "Rosetta", "scoring"),
    "bindcraft": ("plugin_bindcraft", "BindCraft", "workflow_pipeline"),
    "maskrgn": ("plugin_maskrgn", "MaskRGN", "structure_generation"),
}


ROUTE_TEMPLATES = [
    {
        "route_id": "de_novo_insecticidal_protein",
        "label": "De novo insecticidal protein route",
        "best_for": ["insect", "pest", "抗虫", "insecticidal", "toxin", "crop"],
        "summary": "Design compact, specific insect-active proteins, then fold, score, and screen developability liabilities.",
        "modules": ["rfdiffusion", "proteinmpnn", "alphafold2", "rosetta"],
        "risks": [
            "Target species and receptor biology must be explicit before wet-lab claims.",
            "Activity and environmental safety remain experimental validation questions.",
        ],
    },
    {
        "route_id": "scaffold_redesign_stability",
        "label": "Known-scaffold redesign route",
        "best_for": ["redesign", "stability", "solubility", "scaffold", "variant"],
        "summary": "Start from an existing protein scaffold and redesign sequence/stability while preserving functional motifs.",
        "modules": ["proteinmpnn", "alphafold2", "rosetta"],
        "risks": [
            "Template provenance and functional residues must be reviewed before redesign.",
            "Sequence-only gains do not guarantee expression or biological activity.",
        ],
    },
    {
        "route_id": "binder_screening_route",
        "label": "Binder discovery route",
        "best_for": ["binder", "binding", "receptor", "interface", "target"],
        "summary": "Generate interface candidates against a target structure, design sequences, predict complexes, and score interfaces.",
        "modules": ["rfdiffusion", "proteinmpnn", "alphafold2", "rosetta"],
        "risks": [
            "Binding hypotheses require structure and assay context.",
            "Interface scores need orthogonal developability filters.",
        ],
    },
    {
        "route_id": "rapid_structure_triage",
        "label": "Rapid structure triage route",
        "best_for": ["quick", "triage", "fold", "screen", "sequence"],
        "summary": "Use sequence-property checks plus fast structure prediction before committing GPU-heavy generation.",
        "modules": ["alphafold2", "boltz", "rosetta"],
        "risks": [
            "Fast triage can miss rare but promising design mechanisms.",
            "Confidence metrics are not experimental evidence.",
        ],
    },
]


def _project_context(connection: sqlite3.Connection, project_id: str | None) -> dict[str, Any]:
    if not project_id:
        return {"project": None, "research": None, "task": None}
    project = catalog.get_project(connection, project_id)
    return {
        "project": project,
        "research": catalog.get_project_research_summary(connection, project_id),
        "task": catalog.get_project_design_task(connection, project_id),
    }


def _text_blob(project_context: dict[str, Any], target: str | None, objective: str) -> str:
    project = project_context.get("project") or {}
    task = project_context.get("task") or {}
    pieces = [
        target or "",
        objective,
        str(project.get("project_name") or ""),
        str(project.get("project_type") or ""),
        str(project.get("summary") or ""),
        str(task.get("objective") or ""),
    ]
    return " ".join(pieces).lower()


def _plugin_available(connection: sqlite3.Connection, plugin_id: str) -> bool:
    return registry.get_model_plugin(connection, plugin_id) is not None


def _module_payload(connection: sqlite3.Connection, module_id: str, objective: str) -> dict[str, Any]:
    plugin_id, model_name, node_type = PLUGIN_BY_ID[module_id]
    plugin = registry.get_model_plugin(connection, plugin_id) or {}
    parameters = plugin.get("parameter_schema_json") or {}
    return {
        "module_id": module_id,
        "model_plugin_id": plugin_id,
        "model_name": plugin.get("model_name") or model_name,
        "node_type": node_type,
        "available": bool(plugin),
        "summary": plugin.get("description") or f"{model_name} workflow module",
        "default_parameters": {
            "copilot_objective": objective,
            "planner_module_id": module_id,
        },
        "parameter_schema": parameters if isinstance(parameters, dict) else {},
    }


def _score_route(route: dict[str, Any], blob: str) -> int:
    score = 0
    for token in route["best_for"]:
        if token.lower() in blob:
            score += 6
    if "protein" in blob or "蛋白" in blob:
        score += 2
    if route["route_id"] == "de_novo_insecticidal_protein" and ("抗虫" in blob or "insect" in blob):
        score += 10
    return score


def plan_routes(
    connection: sqlite3.Connection,
    *,
    project_id: str | None,
    target: str | None,
    objective: str,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = _project_context(connection, project_id)
    project = context.get("project") or {}
    target_text = target or project.get("project_name") or "new protein target"
    objective_text = objective or project.get("summary") or "Design and validate a protein workflow."
    blob = _text_blob(context, target_text, objective_text)
    kb_query = " ".join([target_text, objective_text, "workflow route protein design"]).strip()
    kb_items = knowledge.search_entries(connection, kb_query, limit=6)
    if len(kb_items) < 3:
        for fallback in ("protein design workflow", "evidence hierarchy", "sequence property screening"):
            for item in knowledge.search_entries(connection, fallback, limit=3):
                if item["knowledge_entry_id"] not in {k["knowledge_entry_id"] for k in kb_items}:
                    kb_items.append(item)

    ranked = sorted(ROUTE_TEMPLATES, key=lambda route: _score_route(route, blob), reverse=True)
    route_options = []
    for index, route in enumerate(ranked[:4], start=1):
        modules = [
            _module_payload(connection, module_id, objective_text)
            for module_id in route["modules"]
            if module_id in PLUGIN_BY_ID
        ]
        route_options.append({
            "route_id": route["route_id"],
            "label": route["label"],
            "rank": index,
            "recommended": index == 1,
            "summary": route["summary"],
            "rationale": [
                f"Matched project context to route signals: {', '.join(route['best_for'][:4])}.",
                "Used curated knowledge entries before selecting model modules.",
                "Kept validation and evidence boundaries explicit before script generation.",
            ],
            "modules": modules,
            "risks": route["risks"],
            "estimated_steps": len(modules),
        })

    legacy_route = [
        module["model_name"]
        for module in (route_options[0]["modules"] if route_options else [])
    ]
    return {
        "mode": "knowledge_guided_rule_planner",
        "project_id": project_id,
        "target": target_text,
        "objective": objective_text,
        "constraints": constraints or {},
        "route": legacy_route,
        "note": "Route options are knowledge-guided; use route_options for selectable routes and modules.",
        "knowledge_context": [
            {
                "knowledge_entry_id": item["knowledge_entry_id"],
                "title": item["title"],
                "category": item["category"],
                "summary": item["summary"],
            }
            for item in kb_items[:6]
        ],
        "analysis_trace": [
            "1. Read project name, type, summary, design task objective, user target, and constraints.",
            "2. Retrieved curated knowledge entries for protein-design evidence, route choice, and developability filters.",
            "3. Ranked route templates by target/objective signals such as insecticidal, scaffold, binder, or triage.",
            "4. Expanded the selected route candidates into concrete model modules with plugin IDs.",
            "5. Returned selectable route options; applying a route creates workflow nodes and edges for script preview/submission.",
        ],
        "route_options": route_options,
    }


def apply_route_plan(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    route_id: str,
    objective: str,
    selected_module_ids: list[str] | None = None,
    target: str | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = plan_routes(
        connection,
        project_id=project_id,
        target=target,
        objective=objective,
        constraints=constraints,
    )
    route = next((item for item in plan["route_options"] if item["route_id"] == route_id), None)
    if route is None:
        raise ValueError("route_not_found")
    selected = selected_module_ids or [item["module_id"] for item in route["modules"] if item.get("available")]
    selected_set = set(selected)
    modules = [item for item in route["modules"] if item["module_id"] in selected_set]
    if not modules:
        raise ValueError("no_modules_selected")

    workflow_run = catalog.create_draft_workflow_run(connection, project_id)
    run_id = workflow_run["workflow_run_id"]
    created_nodes: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        parameters = {
            **(module.get("default_parameters") or {}),
            "model_plugin_id": module["model_plugin_id"],
            "route_id": route_id,
            "route_label": route["label"],
            "target": plan["target"],
            "constraints": constraints or {},
            "knowledge_entry_ids": [item["knowledge_entry_id"] for item in plan["knowledge_context"]],
            "script_preview_ready": True,
        }
        node = catalog.add_workflow_node(
            connection,
            run_id,
            node_type=module["node_type"],
            node_name=module["model_name"],
            model_name=module["model_name"],
            model_version=None,
            parameters_json=json.dumps(parameters),
            position_json=json.dumps({"x": 80 + index * 280, "y": 120 + (index % 2) * 60}),
        )
        created_nodes.append(node)

    edges = [
        {
            "source_node_run_id": created_nodes[index]["node_run_id"],
            "target_node_run_id": created_nodes[index + 1]["node_run_id"],
            "source_port": "output",
            "target_port": "input",
            "edge_type": "data",
            "metadata_json": {"route_id": route_id},
        }
        for index in range(len(created_nodes) - 1)
    ]
    catalog.replace_workflow_edges(connection, run_id, edges)
    layout_nodes = [
        {
            "node_run_id": node["node_run_id"],
            "position": json.loads(node.get("position_json") or "{}"),
        }
        for node in created_nodes
    ]
    catalog.save_workflow_layout(connection, run_id, json.dumps({"nodes": layout_nodes, "edges": edges}))
    connection.execute(
        """
        UPDATE workflow_runs
        SET summary_metrics_json = ?
        WHERE workflow_run_id = ?
        """,
        (
            json.dumps({
                "route": route_id,
                "route_label": route["label"],
                "planner_mode": plan["mode"],
                "module_count": len(created_nodes),
            }),
            run_id,
        ),
    )
    return {
        "workflow_run": catalog.get_workflow_run(connection, run_id),
        "nodes": catalog.list_workflow_nodes(connection, run_id),
        "edges": catalog.list_workflow_edges(connection, run_id),
        "route": route,
        "knowledge_context": plan["knowledge_context"],
        "analysis_trace": plan["analysis_trace"],
    }
