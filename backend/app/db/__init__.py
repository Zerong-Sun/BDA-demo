import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from ..config import DEFAULT_DB_PATH
from ..settings import get_settings
from .pool import get_pool
from .pool import release_connection as _release_from_pool


def database_path() -> Path:
    settings = get_settings()
    if settings.is_postgresql:
        return Path(settings.bda_db_path)
    return Path(os.environ.get("BDA_DB_PATH", DEFAULT_DB_PATH))


def connect_sqlite() -> sqlite3.Connection:
    if get_settings().is_postgresql:
        raise RuntimeError("PostgreSQL mode: use get_db_session() instead of connect_sqlite()")
    return get_pool().acquire()


def connect() -> sqlite3.Connection:
    return connect_sqlite()


def release_connection(connection: sqlite3.Connection) -> None:
    _release_from_pool(connection)


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        release_connection(connection)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
