import json
import re
import sqlite3

from fastapi import APIRouter, Depends

from ..db import get_connection
from ..repositories import catalog
from ..schemas import CandidateExplanationRequest, CopilotChatRequest, ResultInterpretationRequest, RoutePlanRequest
from ..utils.response import envelope

router = APIRouter(prefix="/copilot")

SKILL_KEYWORDS = {
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
        "based on the current demo dataset."
    )


def workflow_adjust_message(connection: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id:
        return "Raise solubility threshold to 88 and cap each scaffold family at 6 ordered variants."
    package = catalog.get_project_delivery_package(connection, project_id)
    constraints = (package or {}).get("redesign_constraints") or {}
    if isinstance(constraints, str):
        constraints = json.loads(constraints)
    preserve = constraints.get("preserve_candidate", "PD1Binder_c4361")
    return (
        f"Preserve {preserve} motif, raise solubility threshold to 88, add hydrophobic patch penalty, "
        "and cap each scaffold family at 6 ordered variants."
    )


def result_interpret_message(connection: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id:
        return "9/48 BLI-positive; SEC aggregation is the main QC loss in the PD-1 demo."
    summary = catalog.get_project_results_summary(connection, project_id)
    return (
        f"{summary['hit_rate_label']}; best BLI Kd is {summary['best_kd']}. "
        f"{summary['main_failure']} explains most QC loss. {summary['decision_detail']}"
    )


def _rule_based_chat(connection: sqlite3.Connection, payload: CopilotChatRequest) -> dict:
    last_message = payload.messages[-1].content if payload.messages else ""
    skill = payload.skill or match_skill(last_message)

    if skill == "workflow-adjust":
        message = workflow_adjust_message(connection, payload.project_id)
    elif skill == "result-interpret":
        message = result_interpret_message(connection, payload.project_id)
    elif skill == "query-candidates":
        message = top_candidates_message(connection, payload.project_id)
    elif skill == "paper-reader":
        message = (
            "Paper database integration is reserved for Phase 2. Indexed methods can be summarized "
            "once an LLM provider is connected."
        )
    elif skill == "structure-explain":
        message = (
            "Explain interface contacts, hydrophobic patches, and developability risks using uploaded "
            "PDB context and candidate structure files."
        )
    else:
        message = top_candidates_message(connection, payload.project_id)

    return {
        "mode": "rule_based_demo",
        "message": message,
        "skill_used": skill,
        "structured": {
            "echo": last_message,
            "project_id": payload.project_id,
        },
    }


@router.post("/route-plan")
def route_plan(payload: RoutePlanRequest, connection: sqlite3.Connection = Depends(get_connection)):
    nodes = catalog.list_workflow_nodes(connection, "run_pd1_round1") if payload.project_id else []
    return envelope({
        "mode": "rule_based_demo",
        "route": [
            "target_intake",
            "RFdiffusion backbone generation",
            "ProteinMPNN sequence design",
            "AlphaFold2 complex prediction",
            "Rosetta relax / interface scoring",
            "BDA filters",
            "Wet-lab validation",
        ],
        "compute_status": "not_connected",
        "note": "Demo mode returns a precomputed PD-1 binder route.",
        "input_summary": payload.model_dump(),
        "existing_node_count": len(nodes),
    })


@router.post("/candidate-explanation")
def candidate_explanation(
    payload: CandidateExplanationRequest,
    connection: sqlite3.Connection = Depends(get_connection),
):
    candidate = catalog.get_candidate(connection, payload.candidate_id)
    reasons = [
        "Strong interface score and pLDDT in the demo batch.",
        "Acceptable SEC profile compared with aggregation-prone families.",
    ]
    recommendation = f"Review {payload.candidate_id} against BLI/SEC evidence before ordering."
    if candidate and candidate.get("decision") == "Anchor":
        recommendation = (
            f"Use {payload.candidate_id} as the round-two motif anchor when BLI/SEC evidence supports it."
        )
        if candidate.get("pred_kd"):
            reasons.insert(0, f"Predicted binding strength: {candidate['pred_kd']}.")
    return envelope({
        "candidate_id": payload.candidate_id,
        "recommendation": recommendation,
        "reasons": reasons,
    })


@router.post("/chat")
async def copilot_chat(payload: CopilotChatRequest, connection: sqlite3.Connection = Depends(get_connection)):
    from ..settings import get_settings

    settings = get_settings()
    if settings.llm_api_key:
        from ..copilot.service import chat_with_llm

        result = chat_with_llm(connection, payload)
        return envelope(result)

    return envelope(_rule_based_chat(connection, payload))


@router.post("/chat/stream")
async def copilot_chat_stream(payload: CopilotChatRequest, connection: sqlite3.Connection = Depends(get_connection)):
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        result = _rule_based_chat(connection, payload)
        yield {"event": "message", "data": json.dumps(result)}

    return EventSourceResponse(event_generator())


@router.post("/chat/sync")
def copilot_chat_sync(payload: CopilotChatRequest, connection: sqlite3.Connection = Depends(get_connection)):
    return copilot_chat(payload, connection)


@router.post("/result-interpretation")
def result_interpretation(
    payload: ResultInterpretationRequest,
    connection: sqlite3.Connection = Depends(get_connection),
):
    summary = catalog.get_project_results_summary(connection, payload.project_id)
    package = catalog.get_project_delivery_package(connection, payload.project_id)
    constraints = (package or {}).get("redesign_constraints") or {}
    if isinstance(constraints, str):
        constraints = json.loads(constraints)
    return envelope({
        "project_id": payload.project_id,
        "summary": f"{summary['hit_rate_label']}; best BLI Kd is {summary['best_kd']}.",
        "round_two_constraints": constraints or {
            "preserve_candidate": summary.get("best_kd_candidate"),
            "increase_scaffold_diversity": True,
            "penalize_exposed_hydrophobic_area": True,
        },
    })


@router.get("/skills")
def list_skills():
    return envelope([
        {"name": "workflow-adjust", "description": "Adjust workflow parameters and constraints"},
        {"name": "result-interpret", "description": "Interpret BLI/SEC experiment results"},
        {"name": "query-candidates", "description": "Query and rank candidates"},
        {"name": "structure-explain", "description": "Explain structure and interface"},
        {"name": "paper-reader", "description": "Literature search and summarization"},
    ])
