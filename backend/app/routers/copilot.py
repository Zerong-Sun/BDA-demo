import json
import sqlite3
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from ..auth.deps import get_current_user, require_role
from ..auth.service import verify_project_access
from ..copilot.biomaterials_skill import (
    BIOMATERIALS_SYSTEM_PROMPT,
    DOMAIN_REFUSAL,
    PROGRAMMABLE_BIOMATERIALS_SKILL,
    is_programmable_biomaterials_question,
)
from ..db import get_connection
from ..repositories import catalog, knowledge, literature, literature_subscriptions
from ..schemas import (
    CandidateExplanationRequest,
    ClaimRelationDetectRequest,
    ClaimReviewRequest,
    ClusterDraftRequest,
    CopilotChatRequest,
    CopilotConfigUpdateRequest,
    LiteratureIngestRequest,
    LiteratureSubscriptionRequest,
    ResultInterpretationRequest,
    RoutePlanRequest,
)
from ..settings import get_settings
from ..utils.response import envelope
from ..copilot import cluster

router = APIRouter(prefix="/copilot")

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


def knowledge_message(connection: sqlite3.Connection, query: str) -> str:
    items = knowledge.search_entries(connection, query, limit=3)
    if not items:
        return (
            "I do not have a matching curated knowledge entry yet. Add a knowledge entry for this method, "
            "model, algorithm, protein, assay, or biomaterial property before relying on Copilot."
        )
    lines = []
    for item in items:
        lines.append(f"- {item['title']}: {item['summary']}")
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


def _rule_based_chat(connection: sqlite3.Connection, payload: CopilotChatRequest) -> dict:
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


def _domain_refusal(project_id: str | None, last_message: str) -> dict:
    return {
        "mode": "domain_guard",
        "message": DOMAIN_REFUSAL,
        "skill_used": "programmable-biomaterials-expert",
        "structured": {
            "echo": last_message,
            "project_id": project_id,
            "allowed_scope": PROGRAMMABLE_BIOMATERIALS_SKILL["description"],
        },
    }


def _resolve_chat(connection: sqlite3.Connection, payload: CopilotChatRequest) -> dict:
    last_message = payload.messages[-1].content if payload.messages else ""
    if last_message and not is_programmable_biomaterials_question(last_message):
        return _domain_refusal(payload.project_id, last_message)
    settings = get_settings()
    if settings.llm_api_key:
        from ..copilot.service import chat_with_llm

        return chat_with_llm(connection, payload)
    return _rule_based_chat(connection, payload)


def _ensure_project_access(connection: sqlite3.Connection, user: dict, project_id: str | None) -> None:
    if project_id and not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=403, detail="forbidden")


def _copilot_config_payload() -> dict:
    settings = get_settings()
    return {
        "llm_api_base": settings.llm_api_base,
        "llm_model": settings.llm_model,
        "api_key_configured": bool(settings.llm_api_key),
        "api_key_preview": f"...{settings.llm_api_key[-4:]}" if settings.llm_api_key else None,
        "system_scope": "programmable_biomaterials_only",
        "system_prompt": BIOMATERIALS_SYSTEM_PROMPT,
    }


@router.get("/config")
def get_copilot_config(_admin: dict = Depends(require_role("admin"))):
    return envelope(_copilot_config_payload())


@router.put("/config")
def update_copilot_config(
    payload: CopilotConfigUpdateRequest,
    _admin: dict = Depends(require_role("admin")),
):
    settings = get_settings()
    if payload.llm_api_base is not None:
        settings.llm_api_base = payload.llm_api_base.strip()
    if payload.llm_model is not None:
        settings.llm_model = payload.llm_model.strip()
    if payload.llm_api_key is not None:
        settings.llm_api_key = payload.llm_api_key.strip()
    return envelope(_copilot_config_payload())


@router.post("/config/test")
def test_copilot_config(
    _admin: dict = Depends(require_role("admin")),
):
    settings = get_settings()
    if not settings.llm_api_key:
        return envelope({
            "connected": False,
            "model": settings.llm_model,
            "reason": "no_api_key",
        })
    try:
        from ..copilot.provider import get_llm_provider

        response = get_llm_provider().chat([
            {"role": "user", "content": "Reply with exactly BDA_OK."}
        ])
        return envelope({
            "connected": True,
            "model": settings.llm_model,
            "sample": response.content[:120],
        })
    except Exception as exc:
        return envelope({
            "connected": False,
            "model": settings.llm_model,
            "reason": str(exc)[:500],
        })


@router.get("/knowledge")
def list_knowledge_entries(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    if q:
        items = knowledge.search_entries(connection, q, category=category, limit=limit)
        return envelope({"items": items, "total": len(items), "limit": limit, "offset": 0, "query": q})
    items, total = knowledge.list_entries(connection, category=category, limit=limit, offset=offset)
    return envelope({"items": items, "total": total, "limit": limit, "offset": offset, "query": q})


@router.get("/knowledge/{knowledge_entry_id}")
def get_knowledge_entry(
    knowledge_entry_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = knowledge.get_entry(connection, knowledge_entry_id)
    if item is None:
        raise HTTPException(status_code=404, detail="knowledge_entry_not_found")
    return envelope(item)


@router.post("/literature/ingest")
def ingest_literature(
    payload: LiteratureIngestRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    from ..services.literature_ingestion import ingest_europe_pmc_query

    try:
        result = ingest_europe_pmc_query(
            connection,
            payload.query,
            limit=payload.limit,
            fetch_full_text=payload.fetch_full_text,
            extract_claims=payload.extract_claims,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"literature_ingestion_failed:{str(exc)[:300]}",
        ) from exc
    return envelope(result)


@router.get("/literature/subscriptions")
def list_literature_subscriptions(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    items = literature_subscriptions.list_subscriptions(connection)
    return envelope({"items": items, "total": len(items)})


@router.post("/literature/subscriptions")
def create_literature_subscription(
    payload: LiteratureSubscriptionRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    admin: dict = Depends(require_role("admin")),
):
    subscription_id = f"subscription_{uuid.uuid4().hex[:12]}"
    connection.execute(
        """
        INSERT INTO literature_subscriptions (
            subscription_id, name, query, enabled, interval_hours,
            result_limit, fetch_full_text, extract_claims, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subscription_id,
            payload.name,
            payload.query,
            int(payload.enabled),
            payload.interval_hours,
            payload.result_limit,
            int(payload.fetch_full_text),
            int(payload.extract_claims),
            admin["user_id"],
        ),
    )
    return envelope(literature_subscriptions.get_subscription(connection, subscription_id))


@router.patch("/literature/subscriptions/{subscription_id}")
def update_literature_subscription(
    subscription_id: str,
    payload: LiteratureSubscriptionRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    if literature_subscriptions.get_subscription(connection, subscription_id) is None:
        raise HTTPException(status_code=404, detail="literature_subscription_not_found")
    connection.execute(
        """
        UPDATE literature_subscriptions
        SET name=?, query=?, enabled=?, interval_hours=?, result_limit=?,
            fetch_full_text=?, extract_claims=?, updated_at=CURRENT_TIMESTAMP
        WHERE subscription_id=?
        """,
        (
            payload.name,
            payload.query,
            int(payload.enabled),
            payload.interval_hours,
            payload.result_limit,
            int(payload.fetch_full_text),
            int(payload.extract_claims),
            subscription_id,
        ),
    )
    return envelope(literature_subscriptions.get_subscription(connection, subscription_id))


@router.post("/literature/subscriptions/{subscription_id}/run")
def run_literature_subscription(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    item = literature_subscriptions.get_subscription(connection, subscription_id)
    if item is None:
        raise HTTPException(status_code=404, detail="literature_subscription_not_found")
    from ..services.literature_subscription_service import run_subscription

    return envelope(run_subscription(connection, item))


@router.get("/literature")
def search_literature_library(
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=10, ge=1, le=50),
    accepted_only: bool = Query(default=False),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items = literature.search_library(
        connection,
        q,
        limit=limit,
        accepted_only=accepted_only,
    )
    return envelope({"items": items, "total": len(items), "query": q})


@router.get("/literature/claims")
def list_literature_claims(
    review_status: str | None = Query(
        default=None,
        pattern="^(accepted|rejected|pending_review)$",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items = literature.list_claims(
        connection,
        review_status=review_status,
        limit=limit,
    )
    return envelope({"items": items, "total": len(items), "review_status": review_status})


@router.post("/literature/relations/detect")
def detect_literature_relations(
    payload: ClaimRelationDetectRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    from ..services.literature_ingestion import detect_claim_relations_with_llm

    try:
        result = detect_claim_relations_with_llm(
            connection,
            limit=payload.limit,
            accepted_only=payload.accepted_only,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"claim_relation_detection_failed:{str(exc)[:300]}",
        ) from exc
    return envelope(result)


@router.get("/literature/relations")
def list_literature_relations(
    review_status: str | None = Query(
        default=None,
        pattern="^(accepted|rejected|pending_review)$",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    items = literature.list_relations(
        connection,
        review_status=review_status,
        limit=limit,
    )
    return envelope({"items": items, "total": len(items), "review_status": review_status})


@router.patch("/literature/relations/{relation_id}")
def review_literature_relation(
    relation_id: str,
    payload: ClaimReviewRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(require_role("admin", "researcher")),
):
    item = literature.review_relation(
        connection,
        relation_id,
        review_status=payload.review_status,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="claim_relation_not_found")
    return envelope(item)


@router.patch("/literature/claims/{claim_id}")
def review_literature_claim(
    claim_id: str,
    payload: ClaimReviewRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(require_role("admin", "researcher")),
):
    item = literature.review_claim(
        connection,
        claim_id,
        review_status=payload.review_status,
        reviewed_by=user["user_id"],
    )
    if item is None:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return envelope(item)


@router.get("/literature/{document_id}")
def get_literature_document(
    document_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    item = literature.get_document(connection, document_id)
    if item is None:
        raise HTTPException(status_code=404, detail="literature_document_not_found")
    return envelope(item)


@router.get("/cluster/drafts")
def list_cluster_drafts(
    project_id: str | None = Query(default=None),
    _user: dict = Depends(get_current_user),
):
    return envelope({"items": cluster.list_drafts(project_id=project_id)})


@router.post("/cluster/drafts")
def create_cluster_draft(
    payload: ClusterDraftRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    try:
        item = cluster.create_draft(
            project_id=payload.project_id,
            created_by=user["user_id"],
            job_name=payload.job_name,
            command=payload.command,
            queue=payload.queue,
            gpu_count=payload.gpu_count,
            cpu_count=payload.cpu_count,
            setup_lines=payload.setup_lines,
            expected_outputs=payload.expected_outputs,
            rationale=payload.rationale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(item)


@router.get("/cluster/drafts/{draft_id}")
def get_cluster_draft(
    draft_id: str,
    _user: dict = Depends(get_current_user),
):
    try:
        return envelope(cluster.refresh_draft(draft_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cluster/drafts/{draft_id}/confirm")
def confirm_cluster_draft(
    draft_id: str,
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        return envelope(cluster.submit_draft(draft_id, confirmed_by=user["user_id"]))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cluster/drafts/{draft_id}/download")
def download_cluster_output(
    draft_id: str,
    path: str = Query(min_length=1, max_length=500),
    _user: dict = Depends(get_current_user),
):
    try:
        filename, content = cluster.download_output(draft_id, path)
    except ValueError as exc:
        status = 404 if str(exc) == "output_not_found" else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/route-plan")
def route_plan(
    payload: RoutePlanRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
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
    _user: dict = Depends(get_current_user),
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
def copilot_chat(
    payload: CopilotChatRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    return envelope(_resolve_chat(connection, payload))


@router.post("/chat/stream")
async def copilot_chat_stream(
    payload: CopilotChatRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    result = await run_in_threadpool(_resolve_chat, connection, payload)

    async def event_generator():
        message = result.get("message", "")
        chunk_size = 24
        for i in range(0, len(message), chunk_size):
            yield {"event": "message", "data": message[i : i + chunk_size]}
        yield {"event": "done", "data": json.dumps({"skill_used": result.get("skill_used"), "mode": result.get("mode")})}

    return EventSourceResponse(event_generator())


@router.post("/chat/sync")
def copilot_chat_sync(
    payload: CopilotChatRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    return envelope(_resolve_chat(connection, payload))


@router.post("/result-interpretation")
def result_interpretation(
    payload: ResultInterpretationRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
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
def list_skills(_user: dict = Depends(get_current_user)):
    return envelope([
        PROGRAMMABLE_BIOMATERIALS_SKILL,
        {"name": "workflow-adjust", "description": "Adjust workflow parameters and constraints"},
        {"name": "result-interpret", "description": "Interpret BLI/SEC experiment results"},
        {"name": "query-candidates", "description": "Query and rank candidates"},
        {"name": "structure-explain", "description": "Explain structure and interface"},
        {"name": "paper-reader", "description": "Literature search and summarization"},
    ])
