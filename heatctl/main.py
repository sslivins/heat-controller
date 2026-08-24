"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from heatctl import scheduler
from heatctl.database import dispose_engine
from heatctl.routers import devices, schedule

logging.basicConfig(level=logging.INFO)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _run_migrations() -> None:  # pragma: no cover -- exercised via docker-compose e2e, not unit tests
    """Apply Alembic migrations up to head.

    This is the single source of truth for schema management -- tests
    use their own in-memory SQLite fixture (see tests/conftest.py) and
    never reach this code path.
    """
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # pragma: no cover -- lifespan not run by httpx test client
    await asyncio.to_thread(_run_migrations)

    scheduler_task = asyncio.create_task(scheduler.run_forever())
    try:
        yield
    finally:
        scheduler_task.cancel()
        await dispose_engine()


app = FastAPI(title="heat-controller", lifespan=lifespan)
app.include_router(devices.router)
app.include_router(schedule.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
