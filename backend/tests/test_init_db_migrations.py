import sqlite3

from backend.scripts import init_db


def test_if_missing_still_applies_schema_to_existing_database(tmp_path, monkeypatch):
    db_path = tmp_path / "existing.sqlite3"
    sqlite3.connect(db_path).close()
    monkeypatch.setattr(init_db, "DB_PATH", db_path)

    init_db.main(["--if-missing"])

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "literature_subscriptions" in tables
    assert "research_campaigns" in tables
    assert "users" in tables
    assert "jobs" in tables
    assert "research_briefs" in tables
    assert "experiment_plans" in tables
