from pathlib import Path

from .settings import REPO_ROOT, get_settings

_settings = get_settings()

DEFAULT_DB_PATH = Path(_settings.bda_db_path) if not _settings.is_postgresql else REPO_ROOT / "db" / "bda.sqlite3"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
UPLOADS_ROOT = ARTIFACTS_ROOT / "uploads"
STRUCTURES_ROOT = ARTIFACTS_ROOT / "structures"
