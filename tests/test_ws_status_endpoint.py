"""/ws/status endpoint: connect, receive initial snapshot, receive broadcast update."""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("GOODHVAC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOODHVAC_DISABLE_ASYNC_VALIDATION", "true")

import pytest
from fastapi.testclient import TestClient

import goodhvac.main as main_module
from goodhvac.models import DeviceStatusCache
from goodhvac.status_poller import status_message
from goodhvac.ws_hub import status_hub


@pytest.fixture
def sync_client(monkeypatch):
    # The real lifespan runs Alembic migrations (Postgres-specific DDL) and
    # starts the scheduler/poller background loops -- none of that applies
    # to this in-memory-SQLite, single-endpoint websocket test, and Alembic's
    # migration DDL isn't SQLite-compatible anyway. Tests exercise the
    # /ws/status route in isolation, same spirit as the ASGITransport
    # `client` fixture used elsewhere, but TestClient is needed here for
    # websocket_connect support.
    monkeypatch.setattr(main_module, "_run_migrations", lambda: None)

    async def _noop_forever() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr(main_module.scheduler, "run_forever", _noop_forever)
    monkeypatch.setattr(main_module.status_poller, "run_forever", _noop_forever)

    with TestClient(main_module.app) as c:
        yield c


def test_ws_status_sends_initial_snapshot(sync_client):
    with sync_client.websocket_connect("/ws/status") as ws:
        message = ws.receive_json()
        assert message["type"] == "snapshot"
        assert message["devices"] == []


def test_ws_status_receives_broadcast_update(sync_client):
    with sync_client.websocket_connect("/ws/status") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"

        cache = DeviceStatusCache(
            device_id=1, state="online", consecutive_failures=0, mode="HEAT", thermostat_state="HEATING"
        )
        status_hub.broadcast(status_message(cache))

        update = ws.receive_json()
        assert update["type"] == "device_status"
        assert update["device_id"] == 1
        assert update["state"] == "online"
