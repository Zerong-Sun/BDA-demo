#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif ! "$PYTHON" -c "import uvicorn" 2>/dev/null; then
  echo "Creating virtualenv and installing backend dependencies..."
  python3 -m venv "$ROOT/.venv"
  PYTHON="$ROOT/.venv/bin/python"
  "$PYTHON" -m pip install -q -r backend/requirements.txt
fi

echo "Initializing database..."
"$PYTHON" backend/scripts/init_db.py

echo "Starting backend on :8100..."
"$PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
if ! curl -sf http://127.0.0.1:8100/api/v1/health >/dev/null; then
  echo "Warning: backend health check failed — check logs above."
fi

echo "Starting frontend on :5173..."
echo ""
echo "Open: http://127.0.0.1:5173/#/experiments?project=proj_pd1_0423"
echo ""

cd frontend
npm install
npm run dev
