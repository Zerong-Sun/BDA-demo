from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..copilot.provider import get_llm_provider
from ..repositories import research_execution, research_planner, registry
from ..settings import get_settings


def _json_response(system: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = get_llm_provider().chat(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, default=str),
            },
        ],
        response_format={"type": "json_object"},
    )
    value = json.loads(response.content)
    if not isinstance(value, dict):
        raise ValueError("llm_planner_invalid_json_object")
    return value


def _latest_research_context(
    connection: sqlite3.Connection,
    research_brief_id: str,
) -> dict[str, Any]:
    runs = research_execution.list_runs(connection, research_brief_id)
    latest_run = (
        research_execution.get_run(connection, runs[0]["research_run_id"])
        if runs else None
    )
    evidence = (latest_run or {}).get("evidence") or []
    return {
        "findings": research_planner.list_findings(connection, research_brief_id),
        "hypotheses": research_execution.list_hypotheses(connection, research_brief_id),
        "evidence": [
            {
                "evidence_link_id": item.get("evidence_link_id"),
                "source_type": item.get("source_type"),
                "source_identifier": item.get("source_identifier"),
                "title": item.get("title"),
                "evidence_level": item.get("evidence_level"),
                "review_status": item.get("review_status"),
                "excerpt": (item.get("evidence_excerpt") or "")[:1200],
            }
            for item in evidence[:80]
        ],
    }


def synthesize_sweet_protein_plan(
    connection: sqlite3.Connection,
    *,
    brief: dict[str, Any],
    canonical_routes: list[dict[str, Any]],
    canonical_nodes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    route_ids = [item["route_id"] for item in canonical_routes]
    node_parameters = {
        item["key"]: item.get("parameters") or {}
        for item in canonical_nodes
    }
    context = _latest_research_context(connection, brief["research_brief_id"])
    result = _json_response(
        """
You are the evidence-driven planning engine for a sweet-protein R&D Copilot.
Return JSON only. Never invent citations, regulatory status, measured sweetness,
receptor activation, safety, or experimental results. Distinguish reviewed
evidence from hypotheses. You may rank only the supplied route IDs and may
recommend parameter values only for keys already present in allowed_node_parameters.
Do not output shell commands, executable code, paths, credentials, or new model names.

Required object:
{
  "selected_route": "one allowed route id",
  "route_assessments": [{
    "route_id": "...",
    "recommendation": "...",
    "rationale": "...",
    "key_risks": ["..."],
    "required_evidence": ["..."],
    "expected_benefits": ["..."]
  }],
  "assumptions": [{"key":"...","value":"...","status":"needs_confirmation|working_assumption"}],
  "risks": [{"risk":"...","severity":"low|medium|high","mitigation":"...","gate":"..."}],
  "success_criteria": [{"stage":"...","criterion":"...","evidence_required":"..."}],
  "receptor_synthesis": {"target":"...","supported_regions":["..."],"uncertainties":["..."]},
  "verification_queue": ["..."],
  "parameter_overrides": {"node_key": {"existing_parameter_key": "value"}},
  "planning_summary": "..."
}
""".strip(),
        {
            "brief": {
                "title": brief.get("title"),
                "objective": brief.get("objective"),
                "product_context": brief.get("product_context"),
                "constraints": brief.get("constraints_json"),
                "source_material": brief.get("source_material_json"),
                "existing_assumptions": brief.get("assumptions_json"),
            },
            "allowed_route_ids": route_ids,
            "canonical_routes": canonical_routes,
            "allowed_node_parameters": node_parameters,
            **context,
        },
    )
    if result.get("selected_route") not in route_ids:
        result["selected_route"] = route_ids[0]
    return result


ALLOWED_RESEARCH_KINDS = {
    "regulatory",
    "uniprot",
    "pdb_and_literature",
    "literature",
}


def decompose_research_questions(brief: dict[str, Any]) -> list[dict[str, Any]] | None:
    if not get_settings().llm_api_key:
        return None
    result = _json_response(
        """
Decompose a sweet-protein product goal into research questions. Return JSON only:
{"questions":[{"track":"...", "question":"...", "priority":10,
"query":{"kind":"regulatory|uniprot|pdb_and_literature|literature",
"term":"...", "terms":["..."], "identifiers":["..."]}}]}
Cover regulation/safety, natural scaffolds, receptor structure/mechanism,
sequence/structure comparison, computational methods, expression/manufacturing,
functional assays, sensory/food matrix, and safety translation.
Queries must be concise and suitable for official databases, Europe PMC,
RCSB PDB, or UniProt. Do not assert findings.
""".strip(),
        {
            "brief": {
                "title": brief.get("title"),
                "objective": brief.get("objective"),
                "product_context": brief.get("product_context"),
                "constraints": brief.get("constraints_json"),
                "source_material": brief.get("source_material_json"),
            },
        },
    )
    questions = []
    for index, raw in enumerate((result.get("questions") or [])[:20]):
        if not isinstance(raw, dict):
            continue
        query = raw.get("query") if isinstance(raw.get("query"), dict) else {}
        if query.get("kind") not in ALLOWED_RESEARCH_KINDS:
            continue
        if query["kind"] == "uniprot" and not query.get("terms"):
            continue
        if query["kind"] in {"pdb_and_literature", "literature"} and not query.get("term"):
            continue
        question = str(raw.get("question") or "").strip()
        track = str(raw.get("track") or "").strip()
        if not question or not track:
            continue
        questions.append({
            "track": track[:80],
            "question": question[:1000],
            "query": query,
            "priority": max(1, min(1000, int(raw.get("priority") or (index + 1) * 10))),
        })
    return questions or None


def synthesize_research_evidence(
    *,
    brief: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not get_settings().llm_api_key or not evidence:
        return None
    evidence_payload = [
        {
            "evidence_link_id": item.get("evidence_link_id"),
            "source_type": item.get("source_type"),
            "source_identifier": item.get("source_identifier"),
            "title": item.get("title"),
            "evidence_level": item.get("evidence_level"),
            "excerpt": (item.get("evidence_excerpt") or "")[:1200],
        }
        for item in evidence[:100]
    ]
    return _json_response(
        """
Synthesize supplied sweet-protein evidence without inventing facts. JSON only:
{
 "findings":[{"track":"...", "title":"...", "statement":"...",
 "evidence_link_ids":["existing id"], "evidence_level":"...",
 "uncertainty":"..."}],
 "hypotheses":[{"hypothesis":"...", "rationale":"...",
 "falsification_test":"...", "evidence_link_ids":["existing id"],
 "confidence":"low|medium|high"}],
 "conflicts":[{"topic":"...","description":"...","evidence_link_ids":["existing id"]}],
 "unresolved_questions":["..."]
}
Use only supplied evidence IDs. Regulatory database records establish record
existence, not automatically a no-questions conclusion or unrestricted use.
Predicted binding does not establish receptor activation, sensory sweetness, or safety.
""".strip(),
        {
            "brief": {
                "objective": brief.get("objective"),
                "constraints": brief.get("constraints_json"),
            },
            "evidence": evidence_payload,
        },
    )


GENERIC_STEP_TEMPLATES = {
    "rf": {"model_name": "RFdiffusion", "node_type": "backbone_generation"},
    "mpnn": {"model_name": "ProteinMPNN", "node_type": "sequence_generation"},
    "af2": {"model_name": "AlphaFold2", "node_type": "fold_prediction"},
    "rosetta": {"model_name": "Rosetta", "node_type": "scoring"},
    "filter": {"model_name": None, "node_type": "selection"},
    "lab": {"model_name": None, "node_type": "experiment"},
}


def plan_generic_workflow(
    connection: sqlite3.Connection,
    *,
    target: str,
    objective: str,
    constraints: dict[str, Any],
    project_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plugins = {
        item["model_name"]: {
            "model_plugin_id": item["model_plugin_id"],
            "model_name": item["model_name"],
            "version": item.get("version"),
            "parameter_schema": item.get("parameter_schema_json"),
        }
        for item in registry.list_model_plugins(connection)
    }
    fallback_steps = [
        {"template_id": "rf", "name": "Backbone generation", "methods": ["RFdiffusion"], "parameters": {"planned_designs": 10000}, "estimate": {"planned": 10000, "unit": "backbones", "duration": "12-24h GPU"}},
        {"template_id": "mpnn", "name": "Sequence design", "methods": ["ProteinMPNN"], "parameters": {"planned_sequences": 1800, "sampling_temp": 0.15}, "estimate": {"planned": 1800, "unit": "sequences", "duration": "1-3h GPU"}},
        {"template_id": "af2", "name": "Fold prediction", "methods": ["AlphaFold2"], "parameters": {"planned_folds": 500}, "estimate": {"planned": 500, "unit": "folds", "duration": "6-16h GPU"}},
        {"template_id": "rosetta", "name": "Rosetta scoring", "methods": ["Rosetta"], "parameters": {"planned_scores": 220}, "estimate": {"planned": 220, "unit": "structures", "duration": "3-8h CPU"}},
        {"template_id": "filter", "name": "Developability filters", "methods": ["quality gates"], "parameters": {"planned_candidates": 48}, "estimate": {"planned": 48, "unit": "candidates", "duration": "1-2h CPU"}},
        {"template_id": "lab", "name": "Experimental validation", "methods": ["expression", "QC", "functional assay"], "parameters": {}, "estimate": {"planned": 48, "unit": "candidates", "duration": "manual planning"}},
    ]
    settings = get_settings()
    if not settings.llm_api_key:
        return {"mode": "validated_fallback", "steps": fallback_steps}
    try:
        result = _json_response(
            """
Create an editable protein-design workflow using only the supplied template IDs.
Return JSON only:
{"summary":"...", "assumptions":["..."], "risks":["..."], "steps":[{
"template_id":"rf|mpnn|af2|rosetta|filter|lab",
"name":"...", "methods":["..."], "parameters":{}, "estimate":{"planned":1,"unit":"...","duration":"..."}
}]}
Use each template at most once and preserve a scientifically sensible order.
Parameters are planning metadata, never shell commands. Do not claim predictions
are experimentally validated.
""".strip(),
            {
                "target_or_goal": target,
                "objective": objective,
                "constraints": constraints,
                "project_context": project_context or {},
                "allowed_templates": GENERIC_STEP_TEMPLATES,
                "registered_plugins": plugins,
            },
        )
        steps = []
        seen: set[str] = set()
        for raw in result.get("steps") or []:
            template_id = raw.get("template_id")
            if template_id not in GENERIC_STEP_TEMPLATES or template_id in seen:
                continue
            seen.add(template_id)
            estimate = raw.get("estimate") if isinstance(raw.get("estimate"), dict) else {}
            parameters = raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {}
            if any(key.lower() in {"command", "shell", "script"} for key in parameters):
                parameters = {
                    key: value for key, value in parameters.items()
                    if key.lower() not in {"command", "shell", "script"}
                }
            steps.append({
                "template_id": template_id,
                "name": str(raw.get("name") or template_id)[:240],
                "methods": [str(item)[:120] for item in (raw.get("methods") or [])[:10]],
                "parameters": parameters,
                "estimate": {
                    "planned": max(1, int(estimate.get("planned") or 1)),
                    "unit": str(estimate.get("unit") or "items")[:80],
                    "duration": str(estimate.get("duration") or "estimate pending")[:120],
                },
            })
        if len(steps) < 2:
            raise ValueError("llm_route_has_too_few_valid_steps")
        return {
            "mode": "llm_validated",
            "summary": result.get("summary"),
            "assumptions": result.get("assumptions") or [],
            "risks": result.get("risks") or [],
            "steps": steps,
        }
    except Exception as exc:
        return {
            "mode": "validated_fallback",
            "fallback_reason": str(exc)[:300],
            "steps": fallback_steps,
        }
