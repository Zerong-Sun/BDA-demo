# BDA Workbench Product Document

**BDA Workbench** is an AI-assisted workbench for protein and biomaterial design automation. It brings target definition, research evidence, model workflows, candidate evaluation, wet-lab feedback, cluster jobs, and delivery packaging into one traceable project space.

In one sentence:

> BDA Workbench turns a research idea into an auditable design plan, executable compute workflow, experiment-ready package, and reusable data asset.

The project has grown beyond the original PD-1 binder demo. The current workspace now covers evidence-driven research planning, sweet protein design exploration, editable workflow DAGs, model plugin schemas, LSF cluster job drafts, artifact tracking, Campaign-based multi-round optimization, and delivery packages.

For the Chinese entry point, see [README.zh-CN.md](README.zh-CN.md).

---

## 1. Product Positioning

BDA Workbench is not a single-model web UI. It is a product and engineering layer for real protein design projects, where every design decision should be connected to evidence, parameters, generated artifacts, experimental feedback, and the next round of work.

### 1.1 Who It Serves

| User | What they care about | What BDA provides |
|------|----------------------|-------------------|
| Computational protein designers | Model routes, parameters, logs, reproducibility | Plugin registry, workflow DAGs, parameter schemas, artifact lineage, job states |
| Wet-lab scientists | Which candidates to test, why, and how to record outcomes | Candidate ranking, experiment templates, result uploads, validation metrics, redesign briefs |
| Project leads / PIs | Progress, risk, hit rate, delivery quality | Project overview, Campaign rounds, decision records, delivery packages |
| Founders / external reviewers | Platform narrative, credibility, extensibility | Demo projects, evidence-backed workflows, roadmap, clear product boundaries |
| Platform and algorithm engineers | How models are connected and operated | Compute adapters, model wrappers, LSF/Docker paths, storage contracts, monitoring |

### 1.2 Product Boundary

BDA Workbench is responsible for engineering the R&D loop:

- Convert a natural-language goal into a structured brief, assumptions, risks, and success criteria.
- Turn literature, databases, structures, sequences, and uploaded notes into reviewable evidence.
- Wrap model capabilities as composable workflow nodes with explicit inputs, parameters, outputs, and validation rules.
- Link candidates, experimental readouts, and failure reasons to next-round design constraints.
- Package project outputs as traceable deliverables instead of loose PDB, FASTA, CSV, JSON, and script folders.

BDA Workbench does **not** treat computational predictions as experimental facts. AlphaFold, Rosetta, docking, language-model scores, and sequence heuristics can support design decisions, but they do not establish binding, sweetness, safety, regulatory status, activity, or developability without proper evidence and experiments.

---

## 2. Current Product Shape

The current repository is a full-stack platform prototype with a usable end-to-end research and design loop.

### 2.1 Frontend Views

| View | Route | Purpose |
|------|-------|---------|
| Experiments | `/experiments` | Project entry, status overview, metrics, next actions |
| Research | `/research` | Literature ingestion, evidence review, reading subscriptions, Campaign operations |
| Workflow | `/workflow` | Visual DAG, model nodes, parameter editing, plugin panel, compute state |
| Candidates | `/candidates` | Candidate table, filters, scoring, explanations, Mol\* structure viewer |
| Results | `/results` | Experiment results, validation metrics, delivery packages, next-round brief |
| Copilot Drawer | Global side panel | Context-aware planning, candidate explanation, cluster script drafts, next-step suggestions |

### 2.2 Backend Capabilities

| Area | Current implementation |
|------|------------------------|
| API gateway | FastAPI under `/api/v1`, covering projects, candidates, experiments, workflow, files, jobs, Copilot, Campaigns, registry, auth, and admin APIs |
| Database | SQLite for local development, Alembic migrations for PostgreSQL |
| Auth and safety | JWT, RBAC, audit logging, security headers, optional rate limits, production configuration checks |
| Artifact management | Upload, download, and tracking for PDB/mmCIF, FASTA, CSV, JSON, XLSX, ZIP, manifests, logs, and reports |
| Model plugins | RFdiffusion, ProteinMPNN, AlphaFold2, and Rosetta wrapper scaffolds and schema contracts |
| Compute adapters | Demo, local, and Docker execution modes, with room for LSF/HPC, HTTP workers, Kubernetes, and cloud backends |
| Copilot | Rule-based engine plus optional OpenAI-compatible LLM provider such as DeepSeek |
| Research | Europe PMC, UniProt, RCSB PDB, Reactome, local literature ingestion, claim/evidence objects, review status |
| Cluster jobs | LSF script drafts, user confirmation, checksum review, submission, status polling, stdout/stderr and artifact collection |
| Campaigns | Multi-round design, experiment feedback, evaluation, parameter patch suggestions, human approval, next-round draft workflows |
| Deployment | Docker Compose, nginx, Redis, Celery, MinIO, PostgreSQL, Prometheus, Grafana |

---

## 3. Core R&D Loop

The platform is organized around the following loop:

```text
Research goal
  -> Brief parsing and assumption review
  -> Evidence search and dossier generation
  -> Route comparison
  -> Editable workflow DAG
  -> Model execution / cluster jobs
  -> Candidate scoring, clustering, and filtering
  -> Wet-lab package and result upload
  -> Campaign evaluation
  -> Next-round constraints and parameter suggestions
```

Copilot proposes plans and explains reasoning. The platform stores evidence, validates parameters, tracks artifacts, runs trusted renderers/adapters, and keeps human review gates in the loop.

---

## 4. Representative Use Cases

### 4.1 Binder Design and Validation

The original seeded project, `proj_pd1_0423`, demonstrates a PD-1 binder loop:

1. Define the PD-1 target, structure template, and interface.
2. Plan a route such as RFdiffusion -> ProteinMPNN -> AlphaFold2 -> Rosetta -> BDA filters -> wet-lab validation.
3. Review ranked candidates, structures, risks, and explanations in the Candidates view.
4. Inspect BLI/SEC-style validation metrics, delivery files, and a second-round redesign brief in Results.

This use case validates the core BDA grammar: task definition, model route, candidate evaluation, experiment feedback, and next-round planning.

### 4.2 Sweet Protein Research Copilot

The current branch adds an evidence-driven planning path for sweet protein design. A user can start with a prompt like:

```text
I want to design an AI-assisted sweet protein for food applications.
Please review natural sweet proteins, regulatory and safety precedents,
sweet taste receptor mechanisms, existing sequences and structures,
then generate an editable computational design and validation workflow.
```

Copilot should help with:

- Clarifying product use, sweetness goal, aftertaste, thermal stability, pH stability, expression host, cost, and regulatory region.
- Building a natural sweet protein scaffold library, including monellin/MNEI, brazzein, thaumatin, mabinlin, miraculin, neoculin, curculin, and emerging candidates.
- Searching and reviewing UniProt, RCSB PDB, Europe PMC, FDA GRAS records, and uploaded internal notes.
- Separating receptor-mechanism evidence from docking, MD, predicted structures, mutagenesis, functional assays, and sensory claims.
- Comparing sequence and structure constraints: residues to preserve, residues that can be redesigned, high-risk regions, and open questions.
- Comparing scaffold redesign, receptor-facing surface redesign, and higher-risk de novo design routes.
- Producing editable workflows, experiment templates, and delivery artifacts.

The sweet protein direction is the key expansion from a binder demo into a broader R&D Copilot.

### 4.3 Campaign-Based Multi-Round Optimization

Campaigns sit above individual workflow DAGs:

```text
Design -> prediction/scoring -> experiment results -> evaluation
  -> parameter patch suggestion -> human approval -> next round
```

Each workflow round remains acyclic and executable. Cross-round feedback is managed by Campaign objects, which keeps the system clean while still representing real iterative R&D.

Current guardrails:

- A round cannot be evaluated while jobs are still running.
- A round should produce one formal evaluation.
- Parameter patches must match registered plugin parameters.
- Continue, retry, and stop actions are proposed decisions first.
- Approved decisions create a next-round draft workflow, not an automatic compute run.
- Wet-lab steps remain human operations with structured result upload.

### 4.4 Cluster Scripts and Model Jobs

The repository now includes `qm-scripts/library/` and a Copilot cluster-job flow to move model execution from ad hoc script folders toward platform-managed jobs:

- Copilot creates LSF script drafts.
- Users review queue, CPU/GPU resources, environment, input paths, commands, and expected outputs.
- The backend stores immutable scripts and SHA-256 checksums.
- Jobs are submitted only after explicit user confirmation.
- The platform polls `bjobs` / `bhist`, then collects stdout, stderr, and output artifacts.

This provides a path for production RFdiffusion, ProteinMPNN, AlphaFold, Boltz, Chai, BindCraft, Rosetta, and internal model jobs.

---

## 5. Product Modules

### 5.1 Target and Product Definition

Turns "what we want to build" into an executable specification:

- Target, species, construct, structure template, chains, and residue ranges.
- Functional goal: binding, inhibition, catalysis, sweet receptor activation, display, stabilization, assembly.
- Product constraints: length, expression host, stability, pH, temperature, cost, regulatory context.
- Success criteria, decision gates, risks, and assumptions that need review.

Future expansion:

- Graphical target-intake forms.
- PDB/UniProt-linked construct boundary selection.
- Target Product Profile templates.
- Project-level requirement versioning and approval.

### 5.2 Research Dossier

Turns research notes and search results into reviewable knowledge objects:

- Literature search, full-text chunking where allowed, claim/evidence extraction.
- Structured sources from UniProt, PDB, Reactome, FDA, and internal materials.
- Findings, hypotheses, assumptions, risks, unresolved questions, and review states.
- Evidence level, source link, applicability, conflicting evidence, and human approval.

Future expansion:

- Vector search over internal knowledge.
- Automated reading subscriptions for selected topics.
- Regulatory database connectors.
- Internal ELN/LIMS and assay result ingestion.

### 5.3 Workflow Orchestration

Represents design routes as editable, validatable, executable DAGs:

- React Flow canvas.
- Node parameters, input/output ports, artifact contracts.
- Plugin registry panel.
- Node status, logs, result files, and gates.
- Workflow plan versions and dependency management.

Future expansion:

- Parallel route comparison.
- Workflow template marketplace.
- Retry and recovery policies.
- Progression modes: suggestion-only, confirm-each-node, gate-driven auto-advance.

### 5.4 Model and Method Plugin Registry

Turns models into platform plugins instead of scattered scripts:

- RFdiffusion for backbone generation, partial diffusion, motif/surface scaffolding.
- ProteinMPNN for sequence design and diversity sampling.
- AlphaFold2, AlphaFold3, Boltz, and Chai for structure and complex prediction.
- Rosetta for relax, interface analysis, scoring, and local design.
- BindCraft, internal models, Mask RGN, XPNN, and future proprietary models.
- Method plugins for BDA filters, developability scoring, sequence properties, structure comparison, experiment parsers, and report generation.

Future expansion:

- Plugin version, license, citation, benchmark, queue, and resource metadata.
- Auto-rendered parameter forms from schemas.
- Output manifest validation.
- Benchmark registry for model and workflow performance.

### 5.5 Candidate Evaluation

Converts large design batches into an experiment-ready candidate set:

- Candidate table, status, priority, score, and filters.
- Mol\* structure viewing.
- Sequence and structure comparison.
- Solubility, aggregation, expression risk, interface confidence, and related metrics.
- Selection rationale, risk explanation, and next action.

Future expansion:

- Multi-objective Pareto ranking.
- Diversity clustering and representative selection.
- Conflict explanation across model scores.
- Active-learning candidate selection.

### 5.6 Wet-Lab Validation and Feedback

Makes experimental feedback a platform asset instead of a report attachment:

- BLI/SPR, SEC, expression, purification, thermostability, functional assay templates.
- CSV, JSON, and XLSX uploads.
- Hit rate, failure categories, candidate outcomes, and round summaries.
- Next-round redesign constraints.

Future expansion:

- ELN/LIMS integration.
- Instrument export parsing.
- Experiment protocol templates.
- Failure attribution models and redesign recommendation engines.

### 5.7 Delivery Package

Turns a project folder into a traceable deliverable:

- FASTA, PDB/mmCIF, score tables, experiment templates, research dossier, workflow graph, workflow plan, and recommendations.
- Source, version, checksum, and project context for every file.
- Different export views for customers, internal research, algorithm review, and audit.

Future expansion:

- Auto-generated PDF/Word project reports.
- Signed and watermarked delivery packages.
- Read-only reviewer/customer spaces.
- Contract milestone and acceptance records.

---

## 6. Important Workspace Assets

| Path | Purpose |
|------|---------|
| `deliverables/sweet_protein_under100aa_20260625/` | Sweet protein under-100-aa research package, inputs, structures, sequences, analysis, and final exports |
| `deliverables/sweet_protein_rfdiffusion_100x2_20260626/` | RFdiffusion design package for monellin and brazzein routes |
| `qm-scripts/library/` | Cluster script library, plugin catalog, example task manifests |
| `docker/models/` | Model container wrappers for RFdiffusion, ProteinMPNN, AlphaFold2, Rosetta |
| `docs/PLAN_甜味蛋白研发Copilot与自动工作流.md` | Sweet protein Copilot and automated workflow plan |
| `docs/COPILOT_科研检索与集群任务指南.md` | Research search, literature learning, cluster jobs, and Campaign guide |
| `docs/PRD02_后端与工作流接入规划.md` | Backend, artifact contract, plugin, compute adapter, and workflow integration plan |
| `docs/DATA_MODEL.md` | Data model documentation |
| `docs/ARCHITECTURE.md` | System architecture |

---

## 7. Technical Architecture

### 7.1 Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query/Table, Zustand, React Router, React Flow, Mol\*, Zod |
| Backend | FastAPI, Pydantic, Uvicorn, structlog |
| Database | SQLite for local development, PostgreSQL for deployment |
| Async jobs | Celery + Redis |
| Artifacts | Local filesystem or MinIO |
| Compute | demo/local/docker adapters, with room for LSF/HPC/remote workers |
| Model wrappers | RFdiffusion, ProteinMPNN, AlphaFold2, Rosetta |
| Auth | JWT + RBAC (`admin`, `researcher`, `viewer`) |
| Copilot | Rule engine plus optional OpenAI-compatible LLM |
| Deployment | Docker Compose, nginx, Prometheus, Grafana |

### 7.2 Repository Layout

```text
BDA/
├── frontend/              # React SPA
├── backend/               # FastAPI, routers, services, repositories, Copilot, compute adapters
├── alembic/               # PostgreSQL migrations
├── docs/                  # Architecture, data model, Copilot, workflow and product docs
├── docker/models/         # Model plugin container wrappers
├── qm-scripts/            # HPC / LSF scripts and task library
├── deliverables/          # Current project delivery packages
├── monitoring/            # Prometheus / Grafana
├── nginx/                 # Reverse proxy config
└── scripts/               # Development, initialization, backup scripts
```

### 7.3 API Groups

| Router | Purpose |
|--------|---------|
| `auth` | Login, users, roles |
| `core` | Projects, targets, candidates, base entities |
| `files` | Uploads, downloads, delivery packages |
| `experiments` | Experiment plans, results, templates |
| `registry` | Model and method plugin registry |
| `compute` | Compute resources, submission, adapters |
| `jobs` | Job state, logs, artifacts |
| `copilot` | Chat, research search, literature learning, cluster drafts |
| `campaigns` | Multi-round evaluation, decisions, next-round drafts |
| `workflow_mgmt` | Workflow plans, graphs, versions, nodes |
| `admin` | Administrative APIs |

---

## 8. Development

### 8.1 Requirements

- Python 3.13
- Node.js 22
- npm
- Optional: Docker / Docker Compose

### 8.2 Local Development

```sh
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py

chmod +x scripts/dev.sh
./scripts/dev.sh
```

Or run the services separately:

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

```sh
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173/#/experiments?project=proj_pd1_0423
```

API docs:

```text
http://127.0.0.1:8100/api/docs
```

### 8.3 Docker Compose

```sh
cp .env.example .env
docker compose up -d
```

| Service | Port | Role |
|---------|------|------|
| `nginx` | 8080 | Unified entry point |
| `api` | 8100 | FastAPI backend |
| `frontend` | 5173 | Frontend SPA |
| `worker` | - | Celery worker |
| `redis` | 6379 | Queue / cache |
| `minio` | 9000 / 9001 | Artifact storage |
| `postgres` | 5432 | PostgreSQL |
| `prometheus` | 9090 | Metrics |
| `grafana` | 3000 | Dashboards |

Default Docker admin:

```text
admin / admin123
```

### 8.4 Key Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BDA_DB_PATH` | `backend/db/bda.sqlite3` | SQLite path or PostgreSQL URL |
| `BDA_COMPUTE_MODE` | `demo` | `demo`, `local`, or `docker` |
| `BDA_ARTIFACTS_BACKEND` | `local` | `local` or MinIO |
| `BDA_JWT_SECRET` | - | JWT signing secret; change in production |
| `VITE_API_BASE` | `/api/v1` | Frontend API base |
| `LLM_API_BASE` / `LLM_API_KEY` | - | Optional OpenAI-compatible LLM provider |
| `LLM_MODEL` | - | Copilot model name |

DeepSeek example:

```dotenv
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-pro
LLM_API_KEY=configure locally; do not commit
```

### 8.5 Tests

```sh
python3 -m pytest backend/tests -q
cd frontend
npm test
```

---

## 9. Roadmap

### Phase 1: Workbench Foundation

Status: largely complete.

- PD-1 binder demo project.
- Experiments, Workflow, Candidates, Results views.
- FastAPI backend, database, auth, candidates, results, files, delivery packages.
- RFdiffusion, ProteinMPNN, AlphaFold2, Rosetta plugin scaffolds.
- Docker Compose, monitoring, MinIO, Redis, Celery.

### Phase 2: Research + Copilot + Workflow Depth

Status: in progress on the current branch.

- Research page and evidence objects.
- Literature ingestion, claim/evidence extraction, review, subscriptions.
- Sweet protein research planner.
- Research briefs, hypotheses, risks, decision gates, success criteria.
- Workflow plan versions, experiment packages, result templates.
- LSF script drafts, review, submission, artifact collection.
- Campaign evaluation and next-round parameter suggestions.

### Phase 3: Production Compute

Status: interfaces are prepared; implementation remains.

- Real GPU and HPC workers.
- Standard artifact mount with `/input/manifest.json` and `/output/manifest.json`.
- Node logs, retry, cancel, resource estimation, and queue management.
- Plugin benchmark, version, license, citation, and resource profiles.
- Cross-model validation with AF2/AF3/Boltz/Chai and related predictors.

### Phase 4: Experiment and Team Operations

Status: product expansion path.

- ELN/LIMS integration.
- Instrument export parsing.
- Project approvals, roles, and read-only customer spaces.
- Experiment protocol templates.
- Multi-team, multi-project, multi-tenant deployments.
- Automatic delivery report generation.

### Phase 5: Data Flywheel and Platformization

Status: long-term direction.

- Cross-project template library.
- Active learning and failure attribution.
- Private knowledge base and vector search.
- Standard benchmark registry.
- Joint versioning of models, data, workflows, and experiments.
- BDA apps for binders, sweet proteins, enzymes, display platforms, protein cages, and biomaterial assemblies.

---

## 10. Expansion Space

The product should not be locked to the PD-1 demo or to a single sweet protein workflow. The architecture should keep the following expansion paths open.

### 10.1 Application Areas

- **Binder platform**: PPI binders, receptor binders, antigen binders, membrane-protein binders.
- **Food proteins and sweet proteins**: natural scaffold redesign, receptor mechanism hypotheses, expression and safety evaluation.
- **Industrial enzymes**: active-site preservation, thermal stability, pH tolerance, solubility, expression optimization.
- **Antigen display and vaccine materials**: nanoparticles, scaffold display, epitope density, conformation control.
- **Protein cages and self-assembling materials**: symmetry, multimer interfaces, assembly routes, stability.
- **Intracellular protein tools**: compact binders, degradation tags, localization signals, expression constraints.

### 10.2 Models and Algorithms

- RFdiffusion / RFdiffusionAA.
- ProteinMPNN / LigandMPNN.
- AlphaFold2 / AlphaFold3.
- Boltz, Chai, ESMFold, and related structure predictors.
- Rosetta, OpenMM, MDAnalysis.
- BindCraft, ColabDesign, protein language model scoring.
- Internal models such as Mask RGN, XPNN, and future proprietary models.

### 10.3 Data and Evidence

- PubMed / Europe PMC / bioRxiv / medRxiv.
- RCSB PDB / UniProt / InterPro / Pfam / Reactome.
- FDA GRAS / EFSA / JECFA and other regulatory sources.
- Patent search.
- Internal experiment records, failed candidates, expression conditions, and assay readouts.

### 10.4 Deployment

- Local demo.
- Single-machine Docker.
- Internal GPU servers.
- LSF / Slurm HPC.
- Kubernetes workers.
- Cloud object storage and managed databases.
- Multi-tenant SaaS or private deployment.

---

## 11. Current Limits and Risks

- Sweetness, receptor activation, safety, and regulatory status require experiments and official evidence; compute alone cannot establish them.
- Literature ingestion and LLM extraction require human review, especially for new papers, preprints, company status, and regulatory claims.
- Production GPU/HPC execution still needs stronger artifact mounting, output manifests, job isolation, resource quotas, and recovery behavior.
- Plugin schemas exist, but full parameter coverage, recommended ranges, defaults, and validation rules still need continuous work.
- Experiment templates exist, but full ELN/LIMS-grade experiment operations remain future work.
- Multi-tenancy, customer spaces, compliance audit, signed delivery, and contract acceptance are productization steps.

---

## 12. Near-Term Priorities

1. Make the Research -> Workflow path robust: a research dossier should generate an editable workflow draft.
2. Turn RFdiffusion into the reference plugin: layered parameters, script preview, checksum, input/output contracts, and clear errors.
3. Build a strong monellin/brazzein sweet protein showcase: evidence, structures, constraints, scripts, candidates, and experiment package.
4. Complete artifact lineage: every PDB, FASTA, CSV, and JSON should trace back to source nodes, parameters, versions, and checksums.
5. Strengthen Campaigns: experimental failure reasons should reliably become next-round constraints and parameter patches.
6. Generate a project report from the platform: research dossier, workflow, candidates, experiment templates, and recommendations.

---

## 13. About BDA+

BDA+ aims to bring protein and biomaterial R&D closer to the engineering discipline of chip design: reproducible, auditable, iterative, and deliverable.

EDA made chips programmable. BDA aims to make biomaterial design programmable.

**Contact:** [contact@bigo.bio](mailto:contact@bigo.bio) · [bigo.bio](https://bigo.bio)

---

## 14. License

Proprietary. © Bigo Biotech. All rights reserved.
