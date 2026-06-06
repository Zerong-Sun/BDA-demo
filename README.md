# BDA Demo

BDA Workbench is a browser-based biomaterial and protein design automation workbench. The first MVP uses a static PD-1 binder demo while keeping the frontend structure ready for backend, compute, and model-plugin integration.

## Repository Layout

- `PRD01_完整产品需求文档.md`: full product requirements.
- `FRD01_前端设计说明.md`: frontend design and acceptance notes.
- `frontend/`: React + TypeScript + Vite app (Phase 1 full-stack upgrade).
- `nolab/`: legacy static frontend demo (archived reference).
- `backend/`: FastAPI API gateway scaffold, SQLite schema, and seeded PD-1 demo data.
- `fig/`: local visual assets used by the demo.
- `backup/`: archived prototype snapshots.

## Current MVP

The current frontend tells one complete loop:

1. Define the PD-1 binder project.
2. Plan a model route with RFdiffusion, ProteinMPNN, AlphaFold2, Rosetta, BDA filters, and wet-lab validation.
3. Rank candidates and explain why `PD1Binder_c4361` anchors the next round.
4. Show BLI/SEC evidence, delivery package contents, and redesign constraints.

## Git Remote

This workspace is connected to:

```sh
origin https://github.com/Zerong-Sun/BDA-demo.git
```

## Backend

Initialize the local database:

```sh
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py
```

Run the API gateway:

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

## Frontend (React)

```sh
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` with the backend running on port `8100`.
