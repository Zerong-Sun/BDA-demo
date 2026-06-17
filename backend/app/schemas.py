from typing import Any

from pydantic import BaseModel, Field


class ApiEnvelope(BaseModel):
    data: Any
    trace_id: str


class RoutePlanRequest(BaseModel):
    project_id: str | None = None
    target: str = "PD-1"
    objective: str = "binder_design"
    constraints: dict[str, Any] = Field(default_factory=dict)


class CandidateExplanationRequest(BaseModel):
    candidate_id: str


class ResultInterpretationRequest(BaseModel):
    project_id: str


class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotChatRequest(BaseModel):
    messages: list[CopilotMessage]
    project_id: str | None = None
    skill: str | None = None


class CopilotConfigUpdateRequest(BaseModel):
    llm_api_base: str | None = Field(default=None, min_length=1)
    llm_api_key: str | None = Field(default=None, min_length=1)
    llm_model: str | None = Field(default=None, min_length=1)


class CandidateResponse(BaseModel):
    candidate_id: str
    project_id: str
    family: str | None = None
    interface_score: float | None = None
    pred_kd: str | None = None
    plddt: float | None = None
    interface_energy: float | None = None
    clash_count: int | None = None
    buried_sasa: float | None = None
    status: str
    decision: str | None = None
    next_action: str | None = None


class ExperimentResultResponse(BaseModel):
    result_id: str
    candidate_id: str
    experiment_type: str
    pass_status: str
    value: str | None = None
    unit: str | None = None
    conclusion: str | None = None
    failure_reason: str | None = None
