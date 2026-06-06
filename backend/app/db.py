import os
import sqlite3
from pathlib import Path
from typing import Iterator

from .config import DEFAULT_DB_PATH
from .settings import get_settings


def database_path() -> Path:
    settings = get_settings()
    if settings.is_postgresql:
        return Path(settings.bda_db_path)
    return Path(os.environ.get("BDA_DB_PATH", DEFAULT_DB_PATH))


def connect_sqlite() -> sqlite3.Connection:
    path = database_path()
    if get_settings().is_postgresql:
        raise RuntimeError("PostgreSQL mode: use get_db_session() instead of connect_sqlite()")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def connect() -> sqlite3.Connection:
    return connect_sqlite()


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
