"""Shared test fixtures: in-memory SQLite DB + FastAPI test client."""

from __future__ import annotations

import os

# Force SQLite before importing anything that reads heatctl.config.settings
# at import time (the settings singleton is constructed once, at import).
os.environ["HEATCTL_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["HEATCTL_DISABLE_ASYNC_VALIDATION"] = "true"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool

import heatctl.database as db_module
from heatctl.database import Base
from heatctl.main import app


@pytest.fixture(autouse=True)
async def _fresh_db(monkeypatch):
    """Rebuild a fresh in-memory SQLite engine per test.

    StaticPool keeps the single in-memory connection alive across the
    session factory's separate connections within one test.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_session_factory", session_factory)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
