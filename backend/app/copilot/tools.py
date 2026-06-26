from __future__ import annotations

import json
import sqlite3

from ..repositories import campaigns, catalog, knowledge, literature, model_catalog, registry
from .cluster import create_draft, refresh_draft
from .research import (
    analyze_reactome_pathways,
    calculate_sequence_properties,
    get_pdb_entry,
    search_literature,
    search_pdb,
    search_uniprot,
)

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
            "name": "search_uniprot",
            "description": "Search curated UniProtKB protein function, organism, gene, length, and pathway annotations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "reviewed_only": {"type": "boolean", "default": True},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_reactome_pathways",
            "description": "Analyze UniProt or gene identifiers against Reactome pathways and return enrichment statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifiers": {"type": "array", "items": {"type": "string"}},
                    "species": {"type": "string", "default": "Homo sapiens"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["identifiers"],
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
    {
        "type": "function",
        "function": {
            "name": "inspect_research_campaign",
            "description": "Inspect a closed-loop research campaign, including rounds, evaluations, proposed decisions, approvals, and next workflow drafts",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                },
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_learned_literature",
            "description": "Search the locally ingested literature library and return traceable claims with evidence excerpts and DOI/PMID identifiers",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "accepted_only": {"type": "boolean", "default": False},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_model_parameters",
            "description": "Inspect a model's canonical adjustable parameters, parameter constraints, and values observed in imported qm-scripts",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_plugin_id": {
                        "type": "string",
                        "description": "Model plugin ID such as plugin_alphafold3 or plugin_proteinmpnn",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model name such as AlphaFold 3, ProteinMPNN, or RFdiffusion",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_literature",
            "description": "Search life-science publications in Europe PMC and return citable metadata and abstracts",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_pdb",
            "description": "Search experimental structures in the RCSB Protein Data Bank",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pdb_entry",
            "description": "Get metadata, method, resolution, citation, and download links for a PDB entry",
            "parameters": {
                "type": "object",
                "properties": {"pdb_id": {"type": "string"}},
                "required": ["pdb_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_sequence_properties",
            "description": "Calculate basic sequence-only protein properties for screening",
            "parameters": {
                "type": "object",
                "properties": {"sequence": {"type": "string"}},
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_cluster_job",
            "description": "Create a reviewable LSF job draft. This does not submit the job and requires explicit user confirmation in the BDA UI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "command": {"type": "string"},
                    "queue": {"type": "string"},
                    "gpu_count": {"type": "integer", "default": 0},
                    "cpu_count": {"type": "integer", "default": 1},
                    "setup_lines": {"type": "array", "items": {"type": "string"}},
                    "expected_outputs": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": ["job_name", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cluster_job_status",
            "description": "Get current LSF status, logs, and output files for a previously created BDA cluster draft",
            "parameters": {
                "type": "object",
                "properties": {"draft_id": {"type": "string"}},
                "required": ["draft_id"],
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

    if name == "inspect_research_campaign":
        campaign_id = str(args.get("campaign_id") or "")
        item = campaigns.get_campaign_detail(connection, campaign_id)
        return item or {"error": "campaign_not_found"}

    if name == "search_learned_literature":
        query = str(args.get("query") or "")
        return {
            "query": query,
            "items": literature.search_library(
                connection,
                query,
                limit=max(1, min(int(args.get("limit") or 5), 20)),
                accepted_only=bool(args.get("accepted_only", False)),
            ),
        }

    if name == "inspect_model_parameters":
        plugin_id = str(args.get("model_plugin_id") or "").strip()
        plugin = registry.get_model_plugin(connection, plugin_id) if plugin_id else None
        if plugin is None:
            requested_name = str(args.get("model_name") or "").strip().lower()
            plugin = next(
                (
                    item
                    for item in registry.list_model_plugins(connection)
                    if str(item.get("model_name") or "").lower() == requested_name
                ),
                None,
            )
        if plugin is None:
            return {"error": "model_plugin_not_found"}
        plugin_id = plugin["model_plugin_id"]
        from .script_importer_bridge import model_parameter_consistency

        return {
            "model": {
                "model_plugin_id": plugin_id,
                "model_name": plugin.get("model_name"),
                "version": plugin.get("version"),
                "description": plugin.get("description"),
                "input_schema": plugin.get("input_schema_json"),
                "output_schema": plugin.get("output_schema_json"),
                "resource_requirement": plugin.get("resource_requirement_json"),
            },
            "parameters": model_catalog.list_parameters(
                connection,
                model_plugin_id=plugin_id,
            ),
            "script_assets": model_catalog.list_script_assets(
                connection,
                model_plugin_id=plugin_id,
            ),
            "script_observations": model_catalog.list_observations(
                connection,
                model_plugin_id=plugin_id,
            ),
            "consistency": model_parameter_consistency(connection, plugin_id),
        }

    if name == "search_literature":
        return search_literature(
            str(args.get("query") or ""),
            limit=int(args.get("limit") or 5),
        )

    if name == "search_pdb":
        return search_pdb(
            str(args.get("query") or ""),
            limit=int(args.get("limit") or 5),
        )

    if name == "get_pdb_entry":
        return get_pdb_entry(str(args.get("pdb_id") or ""))

    if name == "calculate_sequence_properties":
        return calculate_sequence_properties(str(args.get("sequence") or ""))

    if name == "search_uniprot":
        return search_uniprot(
            str(args.get("query") or ""),
            limit=int(args.get("limit") or 5),
            reviewed_only=bool(args.get("reviewed_only", True)),
        )

    if name == "analyze_reactome_pathways":
        identifiers = args.get("identifiers")
        return analyze_reactome_pathways(
            identifiers if isinstance(identifiers, list) else [],
            species=str(args.get("species") or "Homo sapiens"),
            limit=int(args.get("limit") or 10),
        )

    if name == "draft_cluster_job":
        return create_draft(
            project_id=project_id,
            created_by="copilot",
            job_name=str(args.get("job_name") or ""),
            command=str(args.get("command") or ""),
            queue=str(args["queue"]) if args.get("queue") else None,
            gpu_count=int(args.get("gpu_count") or 0),
            cpu_count=int(args.get("cpu_count") or 1),
            setup_lines=args.get("setup_lines") if isinstance(args.get("setup_lines"), list) else [],
            expected_outputs=(
                args.get("expected_outputs")
                if isinstance(args.get("expected_outputs"), list) else []
            ),
            rationale=str(args.get("rationale") or "") or None,
        )

    if name == "get_cluster_job_status":
        return refresh_draft(str(args.get("draft_id") or ""))

    return {"error": "unknown_tool_or_missing_project"}
