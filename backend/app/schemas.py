from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiEnvelope(BaseModel):
    data: Any
    trace_id: str


class RoutePlanRequest(BaseModel):
    project_id: str | None = None
    target: str | None = None
    objective: str = "binder_design"
    constraints: dict[str, Any] = Field(default_factory=dict)


class RoutePlanApplyRequest(BaseModel):
    project_id: str
    route_id: str
    objective: str = Field(min_length=1, max_length=2000)
    selected_module_ids: list[str] = Field(default_factory=list)
    target: str | None = Field(default=None, max_length=200)
    constraints: dict[str, Any] = Field(default_factory=dict)


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=160)
    project_type: str = Field(default="protein_design", min_length=1, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)


class ProjectSyncRequest(BaseModel):
    target: str = Field(default="local", pattern="^(local|cloud)$")


class CandidateExplanationRequest(BaseModel):
    candidate_id: str


class ResultInterpretationRequest(BaseModel):
    project_id: str


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=20000)


class CopilotChatRequest(BaseModel):
    messages: list[CopilotMessage]
    project_id: str | None = None
    skill: str | None = Field(default=None, max_length=120)


class CopilotConfigUpdateRequest(BaseModel):
    llm_api_base: str | None = Field(default=None, min_length=1)
    llm_api_key: str | None = Field(default=None, max_length=4096)
    llm_model: str | None = Field(default=None, min_length=1)


class LiteratureIngestRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)
    fetch_full_text: bool = True
    extract_claims: bool = True


class LiteratureSubscriptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    query: str = Field(min_length=2, max_length=500)
    enabled: bool = True
    interval_hours: int = Field(default=24, ge=1, le=24 * 30)
    result_limit: int = Field(default=5, ge=1, le=10)
    fetch_full_text: bool = True
    extract_claims: bool = True


class ClaimReviewRequest(BaseModel):
    review_status: str = Field(pattern="^(accepted|rejected|pending_review)$")


class ClaimRelationDetectRequest(BaseModel):
    limit: int = Field(default=30, ge=2, le=100)
    accepted_only: bool = False


class CampaignCreateRequest(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=1, max_length=2000)
    initial_workflow_run_id: str | None = None
    max_rounds: int = Field(default=3, ge=1, le=50)
    budget: dict[str, Any] = Field(default_factory=dict)
    stop_conditions: list[dict[str, Any]] = Field(default_factory=list)
    strategy: dict[str, Any] = Field(default_factory=dict)


class CampaignDecisionReviewRequest(BaseModel):
    approve: bool


class CampaignDecisionUpdateRequest(BaseModel):
    parameter_patch: dict[str, Any]
    rationale: str | None = Field(default=None, max_length=4000)


class ClusterDraftRequest(BaseModel):
    project_id: str | None = None
    job_name: str = Field(min_length=1, max_length=64)
    command: str = Field(min_length=1, max_length=2000)
    queue: str | None = Field(default=None, max_length=64)
    gpu_count: int = Field(default=0, ge=0, le=8)
    cpu_count: int = Field(default=1, ge=1, le=128)
    setup_lines: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    rationale: str | None = Field(default=None, max_length=2000)


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
