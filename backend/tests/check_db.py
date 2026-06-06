from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "bda.sqlite3"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        checks = {
            "projects": connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "candidates": connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
            "model_plugins": connection.execute("SELECT COUNT(*) FROM model_plugins").fetchone()[0],
            "compute_nodes": connection.execute("SELECT COUNT(*) FROM compute_nodes").fetchone()[0],
        }
    finally:
        connection.close()
    assert checks["projects"] == 3, checks
    assert checks["candidates"] == 8, checks
    assert checks["model_plugins"] == 4, checks
    assert checks["compute_nodes"] == 2, checks
    print(checks)


if __name__ == "__main__":
    main()

