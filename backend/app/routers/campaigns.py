from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth.deps import get_current_user
from ..auth.service import verify_project_access
from ..db import get_connection
from ..repositories import campaigns
from ..schemas import (
    CampaignCreateRequest,
    CampaignDecisionReviewRequest,
    CampaignDecisionUpdateRequest,
)
from ..services import campaign_service
from ..utils.response import envelope

router = APIRouter()


def _campaign_access(
    connection: sqlite3.Connection,
    user: dict,
    campaign_id: str,
) -> dict:
    item = campaigns.get_campaign(connection, campaign_id)
    if item is None:
        raise HTTPException(status_code=404, detail="campaign_not_found")
    if not verify_project_access(connection, user, item["project_id"]):
        raise HTTPException(status_code=403, detail="forbidden")
    return item


@router.post("/campaigns")
def create_campaign(
    payload: CampaignCreateRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    if not verify_project_access(connection, user, payload.project_id):
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        item = campaign_service.create_campaign(
            connection,
            project_id=payload.project_id,
            name=payload.name,
            objective=payload.objective,
            initial_workflow_run_id=payload.initial_workflow_run_id,
            max_rounds=payload.max_rounds,
            budget=payload.budget,
            stop_conditions=payload.stop_conditions,
            strategy=payload.strategy,
            created_by=user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(item)


@router.get("/projects/{project_id}/campaigns")
def list_campaigns(
    project_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if not verify_project_access(connection, user, project_id):
        raise HTTPException(status_code=403, detail="forbidden")
    items = campaigns.list_project_campaigns(connection, project_id)
    return envelope({"items": items, "total": len(items)})


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    _campaign_access(connection, user, campaign_id)
    return envelope(campaigns.get_campaign_detail(connection, campaign_id))


@router.post("/campaigns/{campaign_id}/rounds/{round_number}/evaluate")
def evaluate_campaign_round(
    campaign_id: str,
    round_number: int,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    _campaign_access(connection, user, campaign_id)
    try:
        result = campaign_service.evaluate_round(connection, campaign_id, round_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(result)


@router.post("/campaign-decisions/{decision_id}/review")
def review_campaign_decision(
    decision_id: str,
    payload: CampaignDecisionReviewRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    decision = campaigns.get_decision(connection, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="campaign_decision_not_found")
    round_item = campaigns.get_round(connection, decision["campaign_round_id"])
    campaign = (
        campaigns.get_campaign(connection, round_item["campaign_id"])
        if round_item else None
    )
    if campaign is None or not verify_project_access(
        connection, user, campaign["project_id"]
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        result = campaign_service.review_decision(
            connection,
            decision_id,
            approve=payload.approve,
            reviewed_by=user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(result)


@router.patch("/campaign-decisions/{decision_id}")
def update_campaign_decision(
    decision_id: str,
    payload: CampaignDecisionUpdateRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="forbidden")
    decision = campaigns.get_decision(connection, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="campaign_decision_not_found")
    round_item = campaigns.get_round(connection, decision["campaign_round_id"])
    campaign = campaigns.get_campaign(connection, round_item["campaign_id"]) if round_item else None
    if campaign is None or not verify_project_access(connection, user, campaign["project_id"]):
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        item = campaign_service.update_proposed_decision(
            connection,
            decision_id,
            parameter_patch=payload.parameter_patch,
            rationale=payload.rationale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(item)
