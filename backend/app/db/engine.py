"""SQLAlchemy async engine for PostgreSQL (optional)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..settings import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def get_async_engine():
    global _engine, _session_factory
    settings = get_settings()
    if not settings.is_postgresql:
        raise RuntimeError("PostgreSQL not configured")
    if _engine is None:
        url = settings.bda_db_path.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(url, echo=False)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    get_async_engine()
    async with _session_factory() as session:
        yield session
