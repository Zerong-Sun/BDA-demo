from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"
SCHEMA = ROOT / "db" / "schema.sql"
SEED = ROOT / "db" / "seed_demo.sql"

MIGRATIONS = [
    "ALTER TABLE workflow_runs ADD COLUMN layout_json TEXT NOT NULL DEFAULT '{\"nodes\":[],\"edges\":[]}'",
    "ALTER TABLE workflow_node_runs ADD COLUMN position_json TEXT NOT NULL DEFAULT '{\"x\":0,\"y\":0}'",
]


def apply_migrations(connection: sqlite3.Connection) -> None:
    for statement in MIGRATIONS:
        try:
            connection.execute(statement)
        except sqlite3.OperationalError:
            pass


def init_db(seed: bool = True) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA.read_text())
        apply_migrations(connection)
        if seed:
            connection.executescript(SEED.read_text())
        connection.commit()
    finally:
        connection.close()
    return DB_PATH


if __name__ == "__main__":
    should_seed = "--no-seed" not in sys.argv
    path = init_db(seed=should_seed)
    print(f"Initialized BDA database: {path}")
