from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "db" / "bda.sqlite3"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
UPLOADS_ROOT = ARTIFACTS_ROOT / "uploads"
STRUCTURES_ROOT = ARTIFACTS_ROOT / "structures"
