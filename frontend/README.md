# BDA Workbench Frontend (React + Vite)

Phase 1 full-stack upgrade for BDA Workbench.

## Stack

- React 18 + TypeScript + Vite
- Mol* protein structure viewer
- React Flow workflow canvas
- TanStack Query + Table
- Zustand state
- Tailwind CSS (dark workbench theme)

## Development

```sh
# Terminal 1 — backend API
cd ../backend
python3 scripts/init_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload

# Terminal 2 — frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

API requests are proxied to `http://127.0.0.1:8100` via `/api`.

## Pages

- `/experiments` — project entry
- `/workflow` — draggable React Flow canvas + PDB upload
- `/candidates` — ranked candidate table + Mol* detail viewer
- `/results` — validation readouts + experiment upload
