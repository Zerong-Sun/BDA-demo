import json
import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from ..auth.deps import get_current_user, require_role
from ..auth.service import verify_project_access
from ..copilot import cluster
from ..copilot.biomaterials_skill import (
    BIOMATERIALS_SYSTEM_PROMPT,
    PROGRAMMABLE_BIOMATERIALS_SKILL,
)
from ..copilot.runtime import resolve_copilot_chat
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
    RoutePlanApplyRequest,
    RoutePlanRequest,
)
from ..services import route_planner
from ..settings import get_settings
from ..utils.response import envelope

router = APIRouter(prefix="/copilot")

COPILOT_CONFIG_NAMESPACE = "copilot"
COPILOT_CONFIG_KEYS = ("llm_api_base", "llm_model", "llm_api_key")


def _ensure_project_access(connection: sqlite3.Connection, user: dict, project_id: str | None) -> None:
    if project_id and not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=403, detail="forbidden")


def _ensure_app_settings_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
          namespace TEXT NOT NULL,
          key TEXT NOT NULL,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (namespace, key)
        )
        """
    )


def _load_persisted_copilot_config(connection: sqlite3.Connection) -> None:
    _ensure_app_settings_table(connection)
    rows = connection.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE namespace = ? AND key IN (?, ?, ?)
        """,
        (COPILOT_CONFIG_NAMESPACE, *COPILOT_CONFIG_KEYS),
    ).fetchall()
    if not rows:
        return
    settings = get_settings()
    for key, value in rows:
        if key == "llm_api_base":
            settings.llm_api_base = value
        elif key == "llm_model":
            settings.llm_model = value
        elif key == "llm_api_key":
            settings.llm_api_key = value


def _persist_copilot_config(connection: sqlite3.Connection, values: dict[str, str]) -> None:
    _ensure_app_settings_table(connection)
    for key, value in values.items():
        if key not in COPILOT_CONFIG_KEYS:
            continue
        connection.execute(
            """
            INSERT INTO app_settings (namespace, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(namespace, key)
            DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (COPILOT_CONFIG_NAMESPACE, key, value),
        )
    connection.commit()


def _copilot_config_payload(connection: sqlite3.Connection | None = None) -> dict:
    if connection is not None:
        _load_persisted_copilot_config(connection)
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
def get_copilot_config(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    return envelope(_copilot_config_payload(connection))


@router.put("/config")
def update_copilot_config(
    payload: CopilotConfigUpdateRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    settings = get_settings()
    updates: dict[str, str] = {}
    if payload.llm_api_base is not None:
        settings.llm_api_base = payload.llm_api_base.strip()
        updates["llm_api_base"] = settings.llm_api_base
    if payload.llm_model is not None:
        settings.llm_model = payload.llm_model.strip()
        updates["llm_model"] = settings.llm_model
    if payload.llm_api_key is not None:
        settings.llm_api_key = payload.llm_api_key.strip()
        updates["llm_api_key"] = settings.llm_api_key
    if updates:
        _persist_copilot_config(connection, updates)
    return envelope(_copilot_config_payload(connection))


@router.post("/config/test")
def test_copilot_config(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    _load_persisted_copilot_config(connection)
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
    user: dict = Depends(require_role("admin", "researcher")),
):
    item = literature.review_relation(
        connection,
        relation_id,
        review_status=payload.review_status,
        reviewed_by=user["user_id"],
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
    return envelope(route_planner.plan_routes(
        connection,
        project_id=payload.project_id,
        target=payload.target,
        objective=payload.objective,
        constraints=payload.constraints,
    ))


@router.post("/route-plan/apply")
def apply_route_plan(
    payload: RoutePlanApplyRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    try:
        return envelope(route_planner.apply_route_plan(
            connection,
            project_id=payload.project_id,
            route_id=payload.route_id,
            objective=payload.objective,
            selected_module_ids=payload.selected_module_ids,
            target=payload.target,
            constraints=payload.constraints,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    _load_persisted_copilot_config(connection)
    return envelope(resolve_copilot_chat(connection, payload))


@router.post("/chat/stream")
async def copilot_chat_stream(
    payload: CopilotChatRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _ensure_project_access(connection, user, payload.project_id)
    _load_persisted_copilot_config(connection)
    result = await run_in_threadpool(resolve_copilot_chat, connection, payload)

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
    _load_persisted_copilot_config(connection)
    return envelope(resolve_copilot_chat(connection, payload))


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
