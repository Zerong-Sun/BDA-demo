from __future__ import annotations

import json
import sqlite3

from ..repositories import catalog, knowledge, literature
from ..settings import get_settings
from .biomaterials_skill import (
    DOMAIN_REFUSAL,
    PROGRAMMABLE_BIOMATERIALS_SKILL,
    is_programmable_biomaterials_question,
)

SKILL_KEYWORDS = {
    "programmable-biomaterials-expert": PROGRAMMABLE_BIOMATERIALS_SKILL["trigger"],
    "workflow-adjust": ["workflow", "route", "threshold", "工作流"],
    "result-interpret": ["bli", "sec", "experiment", "实验", "lab"],
    "query-candidates": ["candidate", "rank", "anchor", "候选", "c4361"],
    "structure-explain": ["structure", "pdb", "interface", "结构"],
    "paper-reader": ["paper", "literature", "citation", "论文"],
}


def match_skill(text: str) -> str:
    lower = text.lower()
    for skill, tokens in SKILL_KEYWORDS.items():
        if any(token.lower() in lower for token in tokens):
            return skill
    return "general"


def top_candidates_message(connection: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id:
        return "Select a project to query ranked candidates."
    items, _ = catalog.list_project_candidates_filtered(
        connection,
        project_id,
        decision="Anchor,Order,Retest",
        limit=5,
    )
    if not items:
        return "No prioritized candidates found for this project."
    names = ", ".join(item["candidate_id"] for item in items[:3])
    return (
        f"Prioritize {names}. They balance interface score, pLDDT, and lower aggregation risk "
        "based on the current project dataset."
    )


def workflow_adjust_message(connection: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id:
        return "Select a project before asking Copilot to adjust workflow constraints."
    package = catalog.get_project_delivery_package(connection, project_id)
    constraints = (package or {}).get("redesign_constraints") or {}
    if isinstance(constraints, str):
        constraints = json.loads(constraints)
    preserve = constraints.get("preserve_candidate", "the best validated motif")
    return (
        f"Preserve {preserve}, raise solubility threshold, add hydrophobic patch penalty, "
        "and cap each scaffold family before ordering."
    )


def result_interpret_message(connection: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id:
        return "Select a project before asking Copilot to interpret experiment results."
    summary = catalog.get_project_results_summary(connection, project_id)
    return (
        f"{summary['hit_rate_label']}; best BLI Kd is {summary['best_kd']}. "
        f"{summary['main_failure']} explains most QC loss. {summary['decision_detail']}"
    )


def project_next_step_message(connection: sqlite3.Connection, project_id: str | None, query: str = "") -> str:
    if not project_id:
        return (
            "Select or create a project first. Then I can use the same Copilot context across research, "
            "workflow, candidates, and results to recommend the next biomaterials action."
        )

    package = catalog.get_project_delivery_package(connection, project_id)
    summary = catalog.get_project_results_summary(connection, project_id)
    if summary:
        return (
            f"For this project, start from the current result decision: {summary['decision_detail']} "
            "Next, review the workflow route and uploaded artifacts, confirm the candidate or scaffold to preserve, "
            "then generate an auditable route plan before submitting compute."
        )
    if package:
        constraints = package.get("redesign_constraints") or {}
        if isinstance(constraints, str):
            constraints = json.loads(constraints)
        preserve = constraints.get("preserve_candidate") or constraints.get("preserve_motif")
        if preserve:
            return (
                f"Keep {preserve} as the design anchor, check that the required structure/sequence files are attached, "
                "then plan a workflow route that records the selected modules and parameters before execution."
            )
    if "file" in query.lower() or "文件" in query:
        return (
            "Check the uploaded artifact list first, select the file to inspect, and connect it to the workflow node "
            "that consumes that format. I will keep that file context available when you move to workflow or results."
        )
    return (
        "Use the current project context to define the target, choose a route from the knowledge base, confirm the "
        "input files and module parameters, then create the workflow graph. I can carry that plan into candidates, "
        "results, and cluster job review."
    )


def knowledge_message(connection: sqlite3.Connection, query: str) -> str:
    items = knowledge.search_entries(connection, query, limit=3)
    if not items:
        return (
            "I do not have a matching curated knowledge entry yet. Add a knowledge entry for this method, "
            "model, algorithm, protein, assay, or biomaterial property before relying on Copilot."
        )
    lines = [f"- {item['title']}: {item['summary']}" for item in items]
    return "Relevant programmable biomaterials knowledge:\n" + "\n".join(lines)


def literature_message(connection: sqlite3.Connection, query: str) -> str:
    items = literature.search_library(connection, query, limit=5)
    if not items:
        return (
            "The local literature library has no matching indexed evidence yet. "
            "An administrator can ingest a Europe PMC query first."
        )
    lines = []
    seen: set[tuple[str, str | None]] = set()
    for item in items:
        identity = (item["document_id"], item.get("claim_id"))
        if identity in seen:
            continue
        seen.add(identity)
        citation = item.get("doi") or (
            f"PMID:{item['pmid']}" if item.get("pmid") else item.get("external_id")
        )
        statement = item.get("statement") or item.get("abstract_text") or "Metadata record"
        lines.append(
            f"- {item['title']} ({item.get('publication_year') or 'n.d.'}; {citation}): "
            f"{statement[:320]}"
        )
    return "Indexed literature evidence:\n" + "\n".join(lines)


def _rule_based_chat(connection: sqlite3.Connection, payload) -> dict:
    last_message = payload.messages[-1].content if payload.messages else ""
    skill = payload.skill or match_skill(last_message)

    if skill == "programmable-biomaterials-expert":
        message = knowledge_message(connection, last_message)
    elif skill == "workflow-adjust":
        message = workflow_adjust_message(connection, payload.project_id)
    elif skill == "result-interpret":
        message = result_interpret_message(connection, payload.project_id)
    elif skill == "query-candidates":
        message = top_candidates_message(connection, payload.project_id)
    elif skill == "paper-reader":
        message = literature_message(connection, last_message)
    elif skill == "structure-explain":
        message = (
            "Explain interface contacts, hydrophobic patches, and developability risks using uploaded "
            "PDB context and candidate structure files."
        )
    else:
        message = project_next_step_message(connection, payload.project_id, last_message)

    return {
        "mode": "rule_based_demo",
        "message": message,
        "skill_used": skill,
        "structured": {
            "echo": last_message,
            "project_id": payload.project_id,
            "copilot_runtime": "single_bda_copilot",
        },
    }


def _domain_refusal(project_id: str | None, last_message: str) -> dict:
    return {
        "mode": "domain_guard",
        "message": DOMAIN_REFUSAL,
        "skill_used": "programmable-biomaterials-expert",
        "structured": {
            "echo": last_message,
            "project_id": project_id,
            "allowed_scope": PROGRAMMABLE_BIOMATERIALS_SKILL["description"],
            "copilot_runtime": "single_bda_copilot",
        },
    }


def resolve_copilot_chat(connection: sqlite3.Connection, payload) -> dict:
    """Single BDA Copilot runtime for guarded chat, tools, and LLM fallback."""
    last_message = payload.messages[-1].content if payload.messages else ""
    if last_message and not is_programmable_biomaterials_question(last_message):
        return _domain_refusal(payload.project_id, last_message)
    if get_settings().llm_api_key:
        from .service import chat_with_llm

        return chat_with_llm(connection, payload)
    return _rule_based_chat(connection, payload)
