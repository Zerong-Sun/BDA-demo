# Data Model

The canonical domain schema is `backend/db/schema.sql`. Authentication and job
tables currently remain in `backend/db/schema_extended.sql`. Alembic migrations
under `alembic/versions/` are the production upgrade path. Demo records are
defined only in `backend/db/seed_demo.sql`.

## Core ownership hierarchy

```text
organization
└── project
    ├── target
    ├── design_task
    │   └── workflow_run
    │       ├── workflow_node_run
    │       │   ├── job
    │       │   └── artifact
    │       └── workflow_edge
    ├── candidate
    │   └── experiment_result
    ├── research_brief
    │   ├── research_question
    │   ├── research_run
    │   │   └── evidence_link
    │   ├── research_finding
    │   ├── design_hypothesis
    │   └── workflow_plan
    │       ├── parameter_recommendation
    │       └── decision_gate
    └── research_campaign
        └── campaign_round
            ├── campaign_evaluation
            └── campaign_decision
```

## Workflow execution

- `workflow_plans` are editable Copilot proposals.
- Materialization creates identity-stable `workflow_runs`,
  `workflow_node_runs`, and `workflow_edges`.
- `jobs` record individual compute attempts; retries create new jobs.
- `artifacts` contain metadata and lineage. Binary content is stored outside
  the database using `artifact://` keys.
- `run_automation_policies` select advisory, confirm-each-node, or
  gate-approved automation.
- `decision_gates` and node statuses prevent compute or experimental stages
  from bypassing review.

## Research and evidence

- `research_briefs` contain objectives, constraints, assumptions, and sources.
- `research_runs` preserve each multi-source retrieval attempt.
- `evidence_links` retain source identifiers, excerpts, evidence level,
  applicability, and human review state.
- `design_hypotheses` separate testable synthesis from established facts.
- `parameter_recommendations` preserve defaults, recommendation, range,
  provenance, confidence, and user-modified state.

## Experimental validation

- `experiment_plans` are attached to workflow plans/runs.
- `experiment_plan_steps` model expression, purification, stability, receptor
  function, sensory, food matrix, process, and safety/regulatory gates.
- A completed step requires a result artifact.
- Human sensory and safety-related work remains independently approved; the
  platform records plans and evidence but does not execute real-world studies.

## Domain catalogs

Reusable reference data is normalized into:

- `protein_scaffolds`
- `receptor_regions`
- `regulatory_precedents`
- `assay_templates`
- `food_matrix_profiles`

These records are templates and evidence indexes, not substitutes for source
verification or regulatory review.

## JSON fields

Flexible scientific and plugin payloads use `*_json` columns. Repository
decoders convert them to native objects. New JSON columns must be registered in
`backend/app/repositories/base.py::JSON_COLUMNS` and covered by tests.

## Data placement policy

| Data | Location |
|---|---|
| Relational metadata and state | SQLite/PostgreSQL |
| Uploaded files and model outputs | local artifact store or MinIO |
| Demo structures | versioned small assets |
| Model checkpoints | image, object store, or cluster filesystem |
| Secrets | environment/secret manager |
| Logs and traces | runtime storage/observability system |
