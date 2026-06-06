# BDA Demo

BDA Workbench is a browser-based biomaterial and protein design automation workbench. The first MVP uses a static PD-1 binder demo while keeping the frontend structure ready for backend, compute, and model-plugin integration.

## Repository Layout

- `docs/PRD01_完整产品需求文档.md`: full product requirements.
- `docs/FRD01_前端设计说明.md`: frontend design and acceptance notes (React app in `frontend/`).
- `docs/PHASE1_ACCEPTANCE.md`: Phase 1 + P1 acceptance checklist.
- `docs/ARCHITECTURE.md`: system architecture overview.
- `frontend/`: React + TypeScript + Vite app (Phase 1 + P1).
- `backend/`: FastAPI API gateway, SQLite schema, seeded PD-1 demo data.
- `fig/`: local visual assets used by the demo.

## Current MVP

The current frontend tells one complete loop:

1. Define the PD-1 binder project.
2. Plan a model route with RFdiffusion, ProteinMPNN, AlphaFold2, Rosetta, BDA filters, and wet-lab validation.
3. Rank candidates and explain why `PD1Binder_c4361` anchors the next round.
4. Show BLI/SEC evidence, delivery package contents, and redesign constraints.

## Quick Start

Initialize the local database:

```sh
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py
```

Run backend + frontend together:

```sh
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Or run separately:

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

```sh
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173?project=proj_pd1_0423` with the backend running on port `8100`.

## Tests

```sh
python3 -m pytest backend/tests/test_api.py -q
cd frontend && npm test
```

## Git Remote

This workspace is connected to:

```sh
origin https://github.com/Zerong-Sun/BDA-demo.git
```
