[English](README.md) | [中文](README.zh-CN.md)

# BDA Workbench

**Biomaterial Design Automation (BDA) platform software for [Bigo](https://bigo.bio)**

> *EDA made chips programmable. Bigo makes biomaterials programmable.*

BDA Workbench is the engineering implementation of Bigo's **BDA+** platform — a design automation system that turns functional requirements for proteins and biomaterials into auditable, experiment-ready engineering tasks. This repository contains the full-stack workbench: project workspace, workflow orchestration, candidate evaluation, wet-lab feedback, and delivery packaging.

---

## Why BDA+

Biomaterial design today is still fragmented. A single binder or display-platform task is often split across 3–5 vendors — design, structure assessment, expression, BLI/SPR, and functional validation — with no single owner accountable for the outcome. Failures are hard to attribute, negative data rarely flows back into the next design round, and projects end with reports instead of reusable assets.

**BDA** covers *how to design*: requirement intake, route selection, candidate generation, risk scoring, and version history in one workflow.

**BDA+** adds *how to validate, diagnose, and iterate*: wet-lab readouts, structured failure attribution, and a closed-loop feedback engine that informs the next candidate ranking.

| Dimension | Traditional fragmented path | BDA+ target path |
|-----------|------------------------------|------------------|
| Accountability | Design, expression, and assay split across vendors | One project boundary from task definition through validation and next-round recommendations |
| Decision-making | Expert judgment + multi-vendor coordination | Task spec, route choice, candidate ranking, and experiment records in a unified project archive |
| Failure handling | Expression or binding failures restart the task from scratch | Failure samples and conditions feed the Feedback Engine and reshape the next ranking |
| Data assets | Reports at project end; negative data rarely reused | Success and failure data structured for cross-task templates |

---

## Platform Modules

BDA+ is organized into six engineering modules. This workbench implements the software layer for each:

| Module | Role in BDA+ | In this repo |
|--------|--------------|--------------|
| **Target & Product Definition** | Define target, antigen, catalytic site, stability, expression, and TPP constraints | Project setup, target profiles, round briefs |
| **Candidate Design Engine** | Generate candidates under task constraints | Workflow canvas with model plugins (RFdiffusion, ProteinMPNN, etc.) |
| **Evaluation Gate** | Filter high-risk candidates before wet lab | BDA scoring filters, structure/function joint ranking |
| **Wet Lab Validation** | Expression, purification, BLI/SPR, activity, assembly | Results view, experiment uploads, validation metrics |
| **Data & Experiment Operations** | Version history, experiment conditions, candidate tags, decisions | SQLite/PostgreSQL schema, audit logs, artifact storage |
| **Closed-Loop Optimization** | Success/failure samples drive next-round design | Round-2 redesign constraints, Copilot explanations, feedback loop |

---

## Application Scope

BDA+ supports two application modes on a shared design engine:

- **Function-driven** — de novo protein drugs, intracellular or membrane binders, industrial enzymes. Deliverables: binding, inhibition, or catalytic function. Near-term proof cases include PPI binders (e.g. BP326), CD3 binders, and riboflavin synthase (RibH) binders.
- **Structure-driven** — antigen display, functional protein presentation, protein crystals, responsive nanocages. Deliverables: controlled conformation, density, geometry, and delivery properties.

The current MVP demonstrates the **binder** workflow with a PD-1 case study. Display platform and industrial enzyme PoC paths share the same BDA grammar with different input constraints and acceptance criteria.

---

## Current MVP: PD-1 Binder Demo

The seeded project `proj_pd1_0423` walks one complete design–validate–iterate loop:

1. **Define** the PD-1 binder project and target profile.
2. **Plan** a workflow route: RFdiffusion → ProteinMPNN → AlphaFold2 → Rosetta → BDA filters → wet-lab validation.
3. **Rank** candidates and explain why `PD1Binder_c4361` anchors the next round.
4. **Validate** with BLI/SEC evidence, delivery package contents, and round-2 redesign constraints.

### UI Views

| Route | Purpose |
|-------|---------|
| `/experiments` | Project entry, overview cards, agent workspace |
| `/workflow` | React Flow canvas, model plugins, compute status, Copilot |
| `/candidates` | Ranked table, filters, Mol\* structure viewer, explanations |
| `/results` | Validation metrics, experiment upload, delivery ZIP, round-2 brief |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query/Table, Zustand, React Router, React Flow, Mol\*, Zod |
| **Backend** | FastAPI, Pydantic, Uvicorn, structlog |
| **Database** | SQLite (local MVP); optional PostgreSQL via `BDA_DB_PATH` |
| **Async jobs** | Celery + Redis |
| **Object storage** | Local filesystem or MinIO |
| **Compute** | Docker model plugins: ProteinMPNN, RFdiffusion, AlphaFold2, Rosetta |
| **Auth** | JWT + RBAC (admin / researcher / viewer) |
| **Copilot** | Rule-based demo engine; optional OpenAI-compatible LLM |
| **Deployment** | Docker Compose, nginx, Prometheus, Grafana |

---

## Quick Start

### Prerequisites

- Python 3.13
- Node.js 22
- npm

### Local development

```sh
# Initialize database and seed demo data
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py

# Run backend + frontend together
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Or run services separately:

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

```sh
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173/#/experiments?project=proj_pd1_0423** (API on port `8100`, proxied via Vite).

### Docker Compose (production-like)

```sh
cp .env.example .env
docker compose up -d
```

| Service | Port | Role |
|---------|------|------|
| `nginx` | 8080 | Unified entry point |
| `api` | 8100 | FastAPI backend |
| `frontend` | 5173 | Built SPA |
| `worker` | — | Celery compute worker |
| `redis` | 6379 | Job broker / cache |
| `minio` | 9000 / 9001 | Artifact storage |
| `postgres` | 5432 | Optional PostgreSQL |
| `prometheus` | 9090 | Metrics |
| `grafana` | 3000 | Dashboards |

Default admin credentials (Docker): `admin` / `admin123`

Set `BDA_COMPUTE_MODE=docker` to submit jobs to real model plugin containers instead of demo mode. For local stub runner tests without Docker, use `BDA_COMPUTE_MODE=local`.

---

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BDA_DB_PATH` | `backend/db/bda.sqlite3` | SQLite path or PostgreSQL URL |
| `BDA_COMPUTE_MODE` | `demo` | `demo` (blocked jobs), `local` (built-in stub runners), or `docker` (real containers) |
| `BDA_ARTIFACTS_BACKEND` | `local` | `local` or MinIO-backed storage |
| `BDA_JWT_SECRET` | — | JWT signing secret (change in production) |
| `VITE_API_BASE` | `/api/v1` | Frontend API base (build-time) |
| `LLM_API_BASE` / `LLM_API_KEY` | — | Optional Copilot LLM provider |

API documentation: **http://127.0.0.1:8100/api/docs**

---

## Repository Layout

```
BDA/
├── docs/                  # Product requirements, architecture, acceptance
├── frontend/              # React SPA (Experiments, Workflow, Candidates, Results)
├── backend/               # FastAPI API gateway, DB schema, Copilot, compute adapters
├── docker/models/         # Model plugin container images
├── models/README.md       # Local-only external model/checkpoint contract
├── alembic/               # PostgreSQL migrations
├── nginx/                 # Reverse proxy config
├── monitoring/            # Prometheus config
├── scripts/dev.sh         # One-command local dev
└── fig/                   # Demo visual assets
```

### Documentation

| Document | Description |
|----------|-------------|
| [`docs/PRD01_完整产品需求文档.md`](docs/PRD01_完整产品需求文档.md) | Full product requirements (vision, users, roadmap) |
| [`docs/FRD01_前端设计说明.md`](docs/FRD01_前端设计说明.md) | Frontend design spec and acceptance criteria |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, API groups, deployment |
| [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) | Source layout, layering, and versioning policy |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Database ownership, workflow, research, and artifact model |
| [`docs/PHASE1_ACCEPTANCE.md`](docs/PHASE1_ACCEPTANCE.md) | Phase 1 + P1 acceptance checklist |

---

## Tests

```sh
python3 -m pytest backend/tests/test_api.py -q
cd frontend && npm test
```

CI runs both suites on push via GitHub Actions (`.github/workflows/ci.yml`).

---

## Roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| **Phase 1 + P1** | Complete | PD-1 demo loop, workflow canvas, candidate ranking, results/delivery, auth, Copilot rules, Docker scaffold |
| **Phase 2** | Planned | Real GPU workers, full LLM Copilot, multi-tenant deployment, cross-task templates |

---

## About Bigo

**Bigo** is building the design automation infrastructure for programmable biomaterials. The team originates from the David Baker protein design ecosystem and commercializes an auditable delivery system — not a single paper or model.

Near-term focus: **platform project delivery** for pharma early-research teams, starting with binder tasks and extending to display platforms and industrial enzyme PoCs. Customers receive candidate packages with sequences, structures, expression data, BLI/SPR readouts, version history, and next-round recommendations — all within a single accountable project boundary.

**Contact:** [contact@bigo.bio](mailto:contact@bigo.bio) · [bigo.bio](https://bigo.bio)

---

## License

Proprietary. © Bigo Biotech. All rights reserved.
