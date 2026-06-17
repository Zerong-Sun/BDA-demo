import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DB_PATH = ROOT / "db" / "bda.sqlite3"
SCHEMA = ROOT / "db" / "schema.sql"
SCHEMA_EXTENDED = ROOT / "db" / "schema_extended.sql"
SEED = ROOT / "db" / "seed_demo.sql"

MIGRATIONS = [
    "ALTER TABLE workflow_runs ADD COLUMN layout_json TEXT NOT NULL DEFAULT '{\"nodes\":[],\"edges\":[]}'",
    "ALTER TABLE workflow_node_runs ADD COLUMN position_json TEXT NOT NULL DEFAULT '{\"x\":0,\"y\":0}'",
    "ALTER TABLE projects ADD COLUMN organization_id TEXT",
]


def apply_migrations(connection: sqlite3.Connection) -> None:
    for statement in MIGRATIONS:
        try:
            connection.execute(statement)
        except sqlite3.OperationalError:
            pass


def seed_admin_user(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT 1 FROM users WHERE username = 'admin' LIMIT 1").fetchone()
    if row:
        return
    from backend.app.auth.service import create_user

    # Bootstrap password is environment-driven; the demo default is only used
    # when BDA_ADMIN_PASSWORD is unset. Set a strong value for any real deployment.
    admin_password = os.environ.get("BDA_ADMIN_PASSWORD", "admin123")
    create_user(
        connection,
        username="admin",
        password=admin_password,
        role="admin",
        display_name="Administrator",
    )

    org_id = "org_default"
    connection.execute(
        "INSERT OR IGNORE INTO organizations (organization_id, name) VALUES (?, ?)",
        (org_id, "Default Organization"),
    )
    user = connection.execute("SELECT user_id FROM users WHERE username = 'admin'").fetchone()
    if user:
        connection.execute(
            "INSERT OR IGNORE INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'admin')",
            (org_id, user["user_id"]),
        )
    connection.execute(
        "UPDATE projects SET organization_id = ? WHERE organization_id IS NULL",
        (org_id,),
    )
    connection.commit()


def register_builtin_plugins(connection: sqlite3.Connection) -> None:
    from backend.app.plugins.defaults import register_default_model_plugins

    register_default_model_plugins(connection)


def init_db(seed: bool = True) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA.read_text())
        if SCHEMA_EXTENDED.exists():
            connection.executescript(SCHEMA_EXTENDED.read_text())
        apply_migrations(connection)
        if seed:
            connection.executescript(SEED.read_text())
            seed_admin_user(connection)
        register_builtin_plugins(connection)
        connection.commit()
    finally:
        connection.close()
    return DB_PATH


if __name__ == "__main__":
    # --if-missing makes container startup safe to run on every boot: it will
    # not re-apply schema/seed (and risk clobbering data) once the DB exists.
    if "--if-missing" in sys.argv and DB_PATH.exists():
        print(f"BDA database already present, skipping init: {DB_PATH}")
        sys.exit(0)
    should_seed = "--no-seed" not in sys.argv
    path = init_db(seed=should_seed)
    print(f"Initialized BDA database: {path}")
