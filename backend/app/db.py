import os
import sqlite3
from pathlib import Path
from typing import Iterator

from .config import DEFAULT_DB_PATH


def database_path() -> Path:
    return Path(os.environ.get("BDA_DB_PATH", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
