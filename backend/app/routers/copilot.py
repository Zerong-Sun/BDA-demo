from uuid import uuid4

from fastapi import APIRouter

from ..schemas import CandidateExplanationRequest, CopilotChatRequest, ResultInterpretationRequest, RoutePlanRequest

router = APIRouter(prefix="/copilot")


def envelope(data):
    return {"data": data, "trace_id": str(uuid4())}


@router.post("/route-plan")
def route_plan(payload: RoutePlanRequest):
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
        "note": "Demo mode returns a precomputed PD-1 binder route; live compute should be submitted through /workflow-runs/{id}/submit-to-compute.",
        "input_summary": payload.model_dump(),
    })


@router.post("/candidate-explanation")
def candidate_explanation(payload: CandidateExplanationRequest):
    return envelope({
        "candidate_id": payload.candidate_id,
        "recommendation": "Use PD1Binder_c4361 as the round-two motif anchor when candidate_id matches the demo lead.",
        "reasons": [
            "Best measured BLI Kd in the demo batch.",
            "Strong interface score and pLDDT.",
            "Acceptable SEC profile compared with aggregation-prone families.",
        ],
    })


@router.post("/chat")
def copilot_chat(payload: CopilotChatRequest):
    last_message = payload.messages[-1].content if payload.messages else ""
    return envelope(
        {
            "mode": "rule_based_demo",
            "message": (
                "Demo Copilot received your request. In Phase 2 this endpoint will call DeepSeek with project, "
                "candidate, and paper-database skills."
            ),
            "skill_used": payload.skill or "general",
            "structured": {
                "echo": last_message,
                "project_id": payload.project_id,
            },
        }
    )


@router.post("/result-interpretation")
def result_interpretation(payload: ResultInterpretationRequest):
    return envelope({
        "project_id": payload.project_id,
        "summary": "9/48 BLI-positive candidates; best BLI Kd is 0.6 nM.",
        "round_two_constraints": {
            "preserve_candidate": "PD1Binder_c4361",
            "increase_scaffold_diversity": True,
            "penalize_exposed_hydrophobic_area": True,
        },
    })

