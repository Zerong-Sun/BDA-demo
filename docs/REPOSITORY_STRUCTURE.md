# Repository Structure

## Source-of-truth layout

```text
BDA/
├── frontend/                 React application and browser-side API client
│   ├── src/app/              Route-level pages
│   ├── src/features/         Domain UI modules
│   ├── src/components/       Reusable UI and visualization components
│   └── src/lib/              API client, schemas, state, and utilities
├── backend/
│   ├── app/routers/          HTTP transport and authorization boundaries
│   ├── app/services/         Workflow and domain orchestration
│   ├── app/repositories/     SQL persistence operations
│   ├── app/plugins/          Model/method plugin manifests
│   ├── app/compute/          Local, Docker, and cluster adapters
│   ├── db/                   Canonical schema and deterministic demo seed
│   ├── scripts/              Database and plugin initialization commands
│   └── tests/                Backend unit and integration tests
├── alembic/                  Ordered production database migrations
├── docker/models/            Platform-owned model runner contracts
├── qm-scripts/               Reviewed cluster-script examples and import seeds
├── docs/                     Product, architecture, data, and operations docs
├── monitoring/               Prometheus and Grafana configuration
├── nginx/                    Reverse-proxy configuration
├── scripts/                  Developer entry points
├── fig/                      Documentation/demo images
└── models/README.md          Contract for local external model installations
```

## Layering rules

Backend dependencies flow inward:

```text
routers → services → repositories → database
             ↓
       compute/plugins/artifact store
```

- Routers validate requests, enforce access, and map domain errors to HTTP.
- Services own workflow transitions, scientific planning, and cross-table
  transactions.
- Repositories own SQL and row serialization.
- Model-specific execution is exposed through plugin manifests and runner
  contracts, not imported directly into API routes.

Frontend dependencies follow:

```text
app pages → feature modules → shared components/lib → API
```

## Versioned versus runtime content

Versioned:

- application source, migrations, schema, tests, documentation;
- model runner adapters and manifests;
- small deterministic demo structures under `backend/artifacts/structures/`
  and `backend/artifacts/complexes/`.

Runtime-only:

- `.env`, SQLite databases, uploaded files, job workspaces and logs;
- coverage, browser traces, caches, virtual environments and build output;
- third-party model checkouts, checkpoints, training data and training output.

Runtime files are excluded by `.gitignore`. Production artifacts should use
MinIO/object storage or a managed shared filesystem.

## Model integration contract

`models/` is not an application package. It is an optional local mount point.
Each platform model must instead provide:

1. a manifest in `backend/app/plugins/defaults.py` or the registry;
2. a trusted runner under `docker/models/<model>/run.py`;
3. an input `manifest.json` contract;
4. an output `manifest.json` containing typed artifact entries;
5. a versioned container image or cluster environment.

This prevents nested repositories and large weights from becoming accidental
application dependencies.
