from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..repositories import experiment_plans, research_planner


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


STEPS = [
    {
        "stage_key": "expression_and_folding",
        "title": "Expression and correct folding",
        "purpose": "Confirm that selected sequences can be produced as correctly folded proteins before functional claims.",
        "samples": ["designed candidates", "natural scaffold baseline"],
        "controls": ["process blank", "negative protein control"],
        "readouts": ["expression yield", "intact mass", "SEC monomer fraction", "folding/disulfide evidence"],
        "acceptance_criteria": ["predefined expression threshold", "identity confirmed", "acceptable monomer fraction"],
        "dependencies": [],
    },
    {
        "stage_key": "purification_quality",
        "title": "Purification and quality",
        "purpose": "Establish purity, recovery, aggregation state, and a food-compatible downstream process concept.",
        "samples": ["expressed candidates"],
        "controls": ["reference purification lot"],
        "readouts": ["purity", "total recovery", "host-cell protein", "residual DNA", "aggregation"],
        "acceptance_criteria": ["project-specific specification approved before execution"],
        "dependencies": ["expression_and_folding"],
    },
    {
        "stage_key": "stability",
        "title": "Stability and formulation window",
        "purpose": "Measure thermal, pH, storage, solubility, and freeze-thaw behavior.",
        "samples": ["purified candidates"],
        "controls": ["natural sweet-protein baseline"],
        "readouts": ["Tm", "monomer retention", "activity retention", "pH window"],
        "acceptance_criteria": ["application-specific stability window"],
        "dependencies": ["purification_quality"],
    },
    {
        "stage_key": "receptor_function",
        "title": "Human sweet-receptor functional assay",
        "purpose": "Distinguish receptor activation from predicted or measured binding.",
        "samples": ["qualified candidates"],
        "controls": [
            "empty-vector cells",
            "single-subunit controls",
            "human TAS1R2/TAS1R3",
            "known sweet-protein positive control",
            "small-molecule positive control",
        ],
        "readouts": ["EC50", "Emax", "Hill coefficient", "pH dependence", "inhibitor sensitivity"],
        "acceptance_criteria": ["reproducible dose response", "receptor-dependent activation"],
        "dependencies": ["purification_quality"],
    },
    {
        "stage_key": "sensory",
        "title": "Approved human sensory evaluation",
        "purpose": "Evaluate sweetness intensity, time-intensity, aftertaste, and off-notes only after safety and ethics review.",
        "samples": ["ethics-approved candidate formulations"],
        "controls": ["defined sucrose equivalents", "approved comparator sweeteners"],
        "readouts": ["recognition threshold", "equivalent sweetness", "time-intensity", "aftertaste", "off-notes"],
        "acceptance_criteria": ["protocol-defined sensory target"],
        "dependencies": ["receptor_function", "safety_regulatory"],
        "safety_level": "requires_ethics_and_safety_approval",
    },
    {
        "stage_key": "food_matrix",
        "title": "Food-matrix validation",
        "purpose": "Measure performance in the intended beverage or food matrix.",
        "samples": ["candidate formulations"],
        "controls": ["matrix without candidate", "current sweetener system"],
        "readouts": ["activity retention", "precipitation", "clarity", "sensory compatibility", "shelf stability"],
        "acceptance_criteria": ["matrix-specific specification"],
        "dependencies": ["stability", "receptor_function"],
    },
    {
        "stage_key": "process",
        "title": "Fermentation and downstream economics",
        "purpose": "Co-optimize production, correct folding, recovery, and effective sweetness titer.",
        "samples": ["lead production strains/lots"],
        "controls": ["baseline host/process"],
        "readouts": ["protein titer", "correct folding fraction", "relative sweetness", "effective sweetness titer", "cost"],
        "acceptance_criteria": ["business-approved cost and process window"],
        "dependencies": ["expression_and_folding", "receptor_function"],
    },
    {
        "stage_key": "safety_regulatory",
        "title": "Safety and regulatory evidence",
        "purpose": "Build a staged safety and regulatory evidence package without assuming animal or human studies are automatically required.",
        "samples": ["finalized candidate and production material"],
        "controls": ["method-specific controls"],
        "readouts": ["allergen/toxin screening", "digestibility", "genotoxicity package", "exposure assessment", "regulatory gap list"],
        "acceptance_criteria": ["regulatory and ethics experts approve next-stage evidence plan"],
        "dependencies": ["purification_quality"],
        "safety_level": "requires_regulatory_review",
    },
]


def build_experiment_plan(
    connection: sqlite3.Connection,
    *,
    workflow_plan_id: str,
    workflow_run_id: str,
    node_run_id: str,
    created_by: str,
) -> dict[str, Any]:
    existing = experiment_plans.get_by_workflow_run(connection, workflow_run_id)
    if existing:
        return existing
    plan = research_planner.get_plan(connection, workflow_plan_id)
    if plan is None:
        raise ValueError("workflow_plan_not_found")
    item = experiment_plans.create_plan(
        connection,
        experiment_plan_id=_id("experiment_plan"),
        project_id=plan["project_id"],
        workflow_plan_id=workflow_plan_id,
        workflow_run_id=workflow_run_id,
        node_run_id=node_run_id,
        title="AI sweet-protein experimental validation plan",
        objective=(
            "Progress candidates through expression, quality, receptor function, "
            "approved sensory, food-matrix, process, and safety/regulatory gates."
        ),
        ethics_requirements=[
            {"stage": "sensory", "requirement": "Independent ethics and informed-consent approval before human participation."},
            {"stage": "animal_or_human_safety", "requirement": "Need determined by regulatory pathway and qualified experts; not auto-scheduled."},
        ],
        regulatory_questions=[
            {"question": "What jurisdiction and intended conditions of use apply?"},
            {"question": "Which safety studies are required after exposure assessment and precedent review?"},
            {"question": "How do sequence changes affect allergenicity and substantial-equivalence arguments?"},
        ],
        result_template={
            "required_columns": ["candidate_id", "stage_key", "metric", "value", "unit", "pass_status", "notes"],
            "accepted_formats": ["csv", "xlsx", "json"],
        },
        created_by=created_by,
    )
    experiment_plans.replace_steps(
        connection,
        item["experiment_plan_id"],
        [
            {"experiment_plan_step_id": _id("experiment_step"), **step}
            for step in STEPS
        ],
    )
    return experiment_plans.get_plan(connection, item["experiment_plan_id"]) or item
