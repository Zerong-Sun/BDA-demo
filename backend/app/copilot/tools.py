from __future__ import annotations

import json
import sqlite3

from ..repositories import catalog, knowledge

COPILOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_candidates",
            "description": "Query ranked candidates for a project",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "description": "Filter by decision e.g. Anchor,Order"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_candidate",
            "description": "Explain why a candidate is recommended",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                },
                "required": ["candidate_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "interpret_results",
            "description": "Interpret BLI/SEC experiment results for a project",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_workflow",
            "description": "Suggest workflow parameter adjustments for round two",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_biomaterials_knowledge",
            "description": "Search curated programmable biomaterials knowledge about methods, models, algorithms, proteins, assays, and material properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {
                        "type": "string",
                        "description": "Optional category such as model, methodology, biomaterial_property, assay",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(
    connection: sqlite3.Connection,
    name: str,
    arguments: str,
    project_id: str | None,
) -> dict:
    args = json.loads(arguments) if arguments else {}

    if name == "query_candidates" and project_id:
        items, total = catalog.list_project_candidates_filtered(
            connection,
            project_id,
            decision=args.get("decision"),
            limit=args.get("limit", 5),
        )
        return {"candidates": items, "total": total}

    if name == "explain_candidate":
        cid = args.get("candidate_id")
        candidate = catalog.get_candidate(connection, cid) if cid else None
        return {"candidate_id": cid, "candidate": candidate}

    if name == "interpret_results" and project_id:
        return catalog.get_project_results_summary(connection, project_id)

    if name == "adjust_workflow" and project_id:
        package = catalog.get_project_delivery_package(connection, project_id)
        return {"redesign_constraints": (package or {}).get("redesign_constraints", {})}

    if name == "search_biomaterials_knowledge":
        query = str(args.get("query") or "")
        category = args.get("category")
        limit = int(args.get("limit") or 5)
        return {
            "query": query,
            "items": knowledge.search_entries(
                connection,
                query,
                category=category if isinstance(category, str) and category else None,
                limit=max(1, min(limit, 10)),
            ),
        }

    return {"error": "unknown_tool_or_missing_project"}
