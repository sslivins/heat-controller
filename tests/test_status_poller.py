"""Status poller hysteresis + generation-safety tests (unit-level, no HTTP)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from goodhvac import device_client, status_poller
from goodhvac.database import session_scope
from goodhvac.device_locks import bump_generation, current_generation
from goodhvac.models import Device, DeviceStatusCache
from goodhvac.schemas import DeviceStatus


@pytest.fixture(autouse=True)
def _reset_locks():
    """device_locks is module-level state shared across tests; clear it between runs."""
    yield
    from goodhvac.device_locks import _generations, _locks

    _locks.clear()
    _generations.clear()


async def _create_device(name="A", host="10.0.0.1") -> int:
    async with session_scope() as session:
        device = Device(name=name, site="S", host=host)
        session.add(device)
        await session.commit()
        await session.refresh(device)
        return device.id


async def test_poll_marks_device_online_on_success(monkeypatch):
    device_id = await _create_device()

    def fake_get_status(device):
        return DeviceStatus(online=True, mode="HEAT", state="HEATING", space_temp=68.0)

    monkeypatch.setattr(device_client, "get_status", fake_get_status)

    await status_poller.poll_once()

    async with session_scope() as session:
        cache = await session.get(DeviceStatusCache, device_id)
        assert cache is not None
        assert cache.state == "online"
        assert cache.consecutive_failures == 0


async def test_poll_hysteresis_degraded_then_offline(monkeypatch):
    """Fewer failures than the threshold => degraded; hitting the threshold => offline."""
    device_id = await _create_device()

    def fake_get_status(device):
        return DeviceStatus(online=False, error="timeout")

    monkeypatch.setattr(device_client, "get_status", fake_get_status)

    # Import here so we read the actual configured threshold instead of hardcoding it.
    from goodhvac.config import settings

    threshold = settings.status_offline_after_failures
    assert threshold >= 2, "test assumes threshold > 1 to exercise the degraded state"

    for _ in range(threshold - 1):
        await status_poller.poll_once()

    async with session_scope() as session:
        cache = await session.get(DeviceStatusCache, device_id)
        assert cache.state == "degraded"
        assert cache.consecutive_failures == threshold - 1

    await status_poller.poll_once()

    async with session_scope() as session:
        cache = await session.get(DeviceStatusCache, device_id)
        assert cache.state == "offline"
        assert cache.consecutive_failures == threshold


async def test_poll_recovers_immediately_to_online(monkeypatch):
    device_id = await _create_device()

    calls = {"n": 0}

    def flaky_get_status(device):
        calls["n"] += 1
        if calls["n"] == 1:
            return DeviceStatus(online=False, error="timeout")
        return DeviceStatus(online=True, mode="HEAT", state="HEATING")

    monkeypatch.setattr(device_client, "get_status", flaky_get_status)

    await status_poller.poll_once()
    await status_poller.poll_once()

    async with session_scope() as session:
        cache = await session.get(DeviceStatusCache, device_id)
        assert cache.state == "online"
        assert cache.consecutive_failures == 0


async def test_poll_skips_disabled_devices(monkeypatch):
    async with session_scope() as session:
        device = Device(name="Disabled", site="S", host="10.0.0.9", enabled=False)
        session.add(device)
        await session.commit()
        await session.refresh(device)
        device_id = device.id

    calls = []
    monkeypatch.setattr(
        device_client, "get_status", lambda device: calls.append(device.id) or DeviceStatus(online=True)
    )

    await status_poller.poll_once()

    assert device_id not in calls
    async with session_scope() as session:
        cache = await session.get(DeviceStatusCache, device_id)
        assert cache is None


async def test_poll_discards_result_if_device_deleted_mid_call(monkeypatch):
    """Generation bump between the semaphore/lock acquire and the blocking call should discard the write."""
    device_id = await _create_device()
    generation_before = current_generation(device_id)

    def fake_get_status(device):
        # Simulate a concurrent delete happening while this "network call" was in flight.
        bump_generation(device_id)
        return DeviceStatus(online=True, mode="HEAT", state="HEATING")

    monkeypatch.setattr(device_client, "get_status", fake_get_status)

    await status_poller.poll_once()

    assert current_generation(device_id) != generation_before
    async with session_scope() as session:
        result = await session.execute(select(DeviceStatusCache).where(DeviceStatusCache.device_id == device_id))
        assert result.scalar_one_or_none() is None


def test_status_message_shape():
    cache = DeviceStatusCache(
        device_id=1,
        state="online",
        mode="HEAT",
        thermostat_state="HEATING",
        space_temp=68.0,
        heat_temp=68.0,
        cool_temp=76.0,
        consecutive_failures=0,
        last_success_at=datetime.now(UTC),
        last_error=None,
        last_error_at=None,
        updated_at=datetime.now(UTC),
    )
    message = status_poller.status_message(cache)
    assert message["type"] == "device_status"
    assert message["device_id"] == 1
    assert message["state"] == "online"
