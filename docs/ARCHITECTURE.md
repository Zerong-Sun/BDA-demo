# BDA Workbench Architecture

## Overview

BDA is a full-stack protein binder design automation platform:

- **Frontend**: React 19 + Vite + TanStack Query + Zustand
- **Backend**: FastAPI + SQLite/PostgreSQL + Celery + Redis
- **Compute**: Docker-based model plugin execution
- **Storage**: Local filesystem or MinIO
- **Auth**: JWT Bearer + RBAC (admin/researcher/viewer)

## API

All endpoints are under `/api/v1/`. OpenAPI docs at `/api/docs`.

### Core groups

| Prefix | Description |
|--------|-------------|
| `/auth` | Login, refresh, user management |
| `/projects` | Project data, candidates, results |
| `/workflow-runs` | Workflow CRUD and layout |
| `/copilot` | AI assistant (rule-based or LLM) |
| `/jobs` | Compute job lifecycle |
| `/admin` | Metrics, audit logs, health detail |

## Deployment

```bash
cp .env.example .env
docker compose up -d
```

Access via `http://localhost:8080` (nginx) or `http://localhost:5173` (dev frontend).

Default admin: `admin` / `admin123`

## Model plugins

Container images in `docker/models/`:

- `bda/proteinmpnn:1.0.0`
- `bda/rfdiffusion:1.1.0`
- `bda/alphafold2:2.3.0`
- `bda/rosetta:2024.09`

Build: `docker build -t bda/proteinmpnn:1.0.0 docker/models/proteinmpnn`

Set `BDA_COMPUTE_MODE=docker` to enable real job submission.
