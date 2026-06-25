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


class ResearchBriefCreateRequest(BaseModel):
    project_id: str
    title: str = Field(default="AI 甜味蛋白研发", min_length=1, max_length=200)
    objective: str = Field(min_length=10, max_length=5000)
    product_context: str = Field(default="food_ingredient", min_length=1, max_length=80)
    constraints: dict[str, Any] = Field(default_factory=dict)
    source_material: list[dict[str, Any]] = Field(default_factory=list)


class ResearchPlanRequest(BaseModel):
    selected_route: str | None = Field(default=None, max_length=80)


class EvidenceReviewRequest(BaseModel):
    review_status: str = Field(pattern="^(accepted|rejected|pending_review)$")


class ResearchFindingReviewRequest(BaseModel):
    review_status: str = Field(pattern="^(accepted|rejected|pending_review)$")


class MarkdownResearchSourceRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=20, max_length=2_000_000)
    source_uri: str | None = Field(default=None, max_length=1000)


class WorkflowPlanMaterializeRequest(BaseModel):
    selected_route: str = Field(min_length=1, max_length=80)


class ExperimentPlanUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    objective: str | None = Field(default=None, min_length=1, max_length=4000)
    status: str | None = Field(default=None, pattern="^(draft|active|completed|archived)$")
    ethics_requirements: list[dict[str, Any]] | None = None
    regulatory_questions: list[dict[str, Any]] | None = None
    result_template: dict[str, Any] | None = None


class ExperimentStepUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    purpose: str | None = Field(default=None, min_length=1, max_length=4000)
    samples: list[Any] | None = None
    controls: list[Any] | None = None
    readouts: list[Any] | None = None
    acceptance_criteria: list[Any] | None = None
    dependencies: list[Any] | None = None
    owner: str | None = Field(default=None, max_length=160)
    status: str | None = Field(default=None, pattern="^(planned|ready|in_progress|completed|blocked)$")
    result_artifact_id: str | None = None
    notes: str | None = Field(default=None, max_length=4000)


class AutomationPolicyUpdateRequest(BaseModel):
    mode: str = Field(default="confirm_each_node", pattern="^(confirm_each_node|auto_after_gate|advisory_only)$")
    auto_submit_ready: bool = False
    notify_on_ready: bool = True
    notify_on_terminal: bool = True
    max_auto_retries: int = Field(default=0, ge=0, le=5)
    retry_backoff_seconds: int = Field(default=60, ge=5, le=3600)


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=160)
    project_type: str = Field(default="protein_design", min_length=1, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)


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
