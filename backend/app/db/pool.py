"""SQLite connection pool for reuse across requests and middleware."""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from queue import Empty, Full, Queue

from ..config import DEFAULT_DB_PATH
from ..settings import get_settings

_pool: SQLiteConnectionPool | None = None
_pool_lock = threading.Lock()


class SQLiteConnectionPool:
    def __init__(self, path: Path, *, size: int = 5) -> None:
        self._path = path
        self._size = size
        self._queue: Queue[sqlite3.Connection] = Queue(maxsize=size)
        for _ in range(size):
            self._queue.put(self._create_connection())

    def _create_connection(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self._path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def acquire(self, *, timeout: float = 5.0) -> sqlite3.Connection:
        try:
            return self._queue.get(timeout=timeout)
        except Empty as exc:
            raise RuntimeError("sqlite_connection_pool_exhausted") from exc

    def release(self, connection: sqlite3.Connection) -> None:
        try:
            self._queue.put_nowait(connection)
        except Full:
            connection.close()


def database_path() -> Path:
    settings = get_settings()
    if settings.is_postgresql:
        return Path(settings.bda_db_path)
    return Path(os.environ.get("BDA_DB_PATH", DEFAULT_DB_PATH))


def get_pool() -> SQLiteConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                if get_settings().is_postgresql:
                    raise RuntimeError("SQLite pool is unavailable when PostgreSQL is configured")
                _pool = SQLiteConnectionPool(database_path())
    return _pool


def release_connection(connection: sqlite3.Connection) -> None:
    get_pool().release(connection)


def reset_pool() -> None:
    """Release the global pool (used in tests)."""
    global _pool
    with _pool_lock:
        _pool = None
