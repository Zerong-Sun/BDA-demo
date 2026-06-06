from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"
SCHEMA = ROOT / "db" / "schema.sql"
SEED = ROOT / "db" / "seed_demo.sql"


def init_db(seed: bool = True) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA.read_text())
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

