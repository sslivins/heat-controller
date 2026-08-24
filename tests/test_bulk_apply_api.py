"""Bulk device control (POST /devices/bulk-apply) tests."""

from __future__ import annotations

import asyncio

import pytest
from pyvenstar import VenstarConnectionError

from heatctl import device_client


async def _create_device(client, name="A", host="10.0.0.1", enabled=True):
    resp = await client.post(
        "/devices",
        json={"name": name, "site": "S", "host": host, "enabled": enabled},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_bulk_apply_success(client, monkeypatch):
    device_id = await _create_device(client)

    calls = []

    def fake_apply(device, mode, heat_temp, cool_temp):
        calls.append((device.id, mode, heat_temp, cool_temp))

    monkeypatch.setattr(device_client, "apply_bulk_action", fake_apply)

    resp = await client.post(
        "/devices/bulk-apply",
        json={"device_ids": [device_id], "mode": "HEAT", "heat_temp": 68.0},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results == [{"device_id": device_id, "outcome": "applied", "error": None}]
    assert calls == [(device_id, "HEAT", 68.0, None)]


async def test_bulk_apply_unknown_device_rejected(client):
    resp = await client.post("/devices/bulk-apply", json={"device_ids": [999], "mode": "HEAT"})
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["outcome"] == "rejected"
    assert result["device_id"] == 999


async def test_bulk_apply_disabled_device_skipped(client):
    device_id = await _create_device(client, enabled=False)

    resp = await client.post("/devices/bulk-apply", json={"device_ids": [device_id], "mode": "HEAT"})
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["outcome"] == "skipped_disabled"


async def test_bulk_apply_unreachable_device(client, monkeypatch):
    device_id = await _create_device(client)

    def fake_apply(device, mode, heat_temp, cool_temp):
        raise VenstarConnectionError("connection refused")

    monkeypatch.setattr(device_client, "apply_bulk_action", fake_apply)

    resp = await client.post("/devices/bulk-apply", json={"device_ids": [device_id], "mode": "HEAT"})
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["outcome"] == "unreachable"
    assert "connection refused" in result["error"]


async def test_bulk_apply_timeout(client, monkeypatch):
    device_id = await _create_device(client)

    def fake_apply(device, mode, heat_temp, cool_temp):
        import time

        time.sleep(0.2)

    monkeypatch.setattr(device_client, "apply_bulk_action", fake_apply)

    # Patch the timeout down so the test doesn't need to wait 15s.
    import heatctl.routers.devices as devices_router

    original_wait_for = asyncio.wait_for

    async def short_wait_for(coro, timeout):
        return await original_wait_for(coro, timeout=0.01)

    monkeypatch.setattr(devices_router.asyncio, "wait_for", short_wait_for)

    resp = await client.post("/devices/bulk-apply", json={"device_ids": [device_id], "mode": "HEAT"})
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["outcome"] == "timed_out"


async def test_bulk_apply_runs_devices_concurrently(client, monkeypatch):
    """Two slow devices should be applied in parallel, not sequentially."""
    device_a = await _create_device(client, name="A", host="10.0.0.1")
    device_b = await _create_device(client, name="B", host="10.0.0.2")

    def fake_apply(device, mode, heat_temp, cool_temp):
        import time

        time.sleep(0.2)

    monkeypatch.setattr(device_client, "apply_bulk_action", fake_apply)

    import time as time_module

    start = time_module.monotonic()
    resp = await client.post(
        "/devices/bulk-apply", json={"device_ids": [device_a, device_b], "mode": "HEAT"}
    )
    elapsed = time_module.monotonic() - start

    assert resp.status_code == 200
    assert all(r["outcome"] == "applied" for r in resp.json()["results"])
    # If run sequentially this would take >= 0.4s; parallel should be close to 0.2s.
    assert elapsed < 0.35


@pytest.fixture(autouse=True)
def _reset_locks():
    """Bulk-apply tests share the module-level device_locks dicts across tests; clear between runs."""
    yield
    from heatctl.device_locks import _generations, _locks

    _locks.clear()
    _generations.clear()
