#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Initializing database..."
python3 backend/scripts/init_db.py

echo "Starting backend on :8100..."
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting frontend on :5173..."
cd frontend
npm install
npm run dev
