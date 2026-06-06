# BDA Backend

MVP backend scaffold for the BDA Workbench.

## Shape

- FastAPI API gateway on `localhost:8100`.
- SQLite database for local MVP data in `backend/db/bda.sqlite3`.
- Repository layer under `app/repositories`.
- Route layer under `app/routers`.
- Compute endpoints return `blocked` until CPU/GPU workers are connected.

## Initialize Database

```sh
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py
```

## Run API

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

Key endpoints:

- `GET /health`
- `GET /projects`
- `GET /projects/proj_pd1_0423/candidates`
- `GET /workflow-runs/run_pd1_round1/nodes`
- `GET /compute-nodes`
- `GET /model-plugins`
- `POST /workflow-runs/run_pd1_round1/submit-to-compute`

