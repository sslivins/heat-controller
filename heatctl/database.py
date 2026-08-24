"""Async SQLAlchemy engine/session plumbing.

Deliberately small — this is a single-service app, not a shared
package used by multiple images, so there's no separate ``shared``
layer like agora-cms has.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from heatctl.config import settings


class Base(DeclarativeBase):
    pass


_engine = create_async_engine(settings.database_url, future=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with _session_factory() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for a session outside of a FastAPI request (e.g. the scheduler loop)."""
    async with _session_factory() as session:
        yield session


async def dispose_engine() -> None:
    await _engine.dispose()
