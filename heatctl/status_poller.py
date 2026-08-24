"""Background status poller: the only path that writes DeviceStatusCache rows.

Runs as its own asyncio task (separate from the scheduler loop -- see
design notes below), polling every enabled device on a fixed interval,
bounded to N concurrent in-flight device calls via a semaphore so a
50-device fleet never floods the LAN or the event loop.

Design notes (see session design review):
- Separate loop from the scheduler: polling and scheduled-apply have
  different cadence and failure semantics; a slow device poll must
  never delay a time-sensitive scheduled setpoint change.
- Per-device lock (heatctl.device_locks) shared with the scheduler and
  bulk-apply endpoint -- if a write is in flight for a device, its poll
  is skipped for this cycle rather than blocking or racing pyvenstar's
  HTTP session.
- Hysteresis: a device only flips to "offline" after
  settings.status_offline_after_failures consecutive failed polls, not
  on the first dropped packet. One success immediately restores
  "online". In between it's "degraded" -- shown as trouble in the UI,
  but distinguishable from a real prolonged outage.
- Generation check: if a device is deleted mid-poll (device_locks
  bump_generation), the result is discarded instead of upserting a
  cache row (or broadcasting) for a device that's already gone.
- Every meaningful state change is persisted to Postgres so a process
  restart shows "last known status as of <time>", not a false "online".
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from heatctl import device_client
from heatctl.config import settings
from heatctl.database import session_scope
from heatctl.device_locks import current_generation, lock_for
from heatctl.models import Device, DeviceStatusCache
from heatctl.ws_hub import status_hub

logger = logging.getLogger("heatctl.status_poller")


async def run_forever() -> None:
    logger.info(
        "Status poller starting, interval=%ss concurrency=%s",
        settings.status_poll_interval_seconds,
        settings.status_poll_concurrency,
    )
    while True:
        try:
            await poll_once()
        except Exception:  # noqa: BLE001 -- one bad cycle must never kill the loop
            logger.exception("Status poll cycle failed")
        await asyncio.sleep(settings.status_poll_interval_seconds)


async def poll_once() -> int:
    """Poll every enabled device once, bounded by settings.status_poll_concurrency. Returns count polled."""
    async with session_scope() as session:
        result = await session.execute(select(Device).where(Device.enabled.is_(True)))
        device_ids = [d.id for d in result.scalars().all()]

    semaphore = asyncio.Semaphore(settings.status_poll_concurrency)
    await asyncio.gather(*(_poll_device(device_id, semaphore) for device_id in device_ids), return_exceptions=True)
    return len(device_ids)


async def _poll_device(device_id: int, semaphore: asyncio.Semaphore) -> None:
    generation = current_generation(device_id)
    lock = lock_for(device_id)

    if lock.locked():
        # A write (scheduled or bulk apply) is in flight for this device --
        # skip this cycle rather than blocking on it or racing pyvenstar's
        # session. We'll catch it on the next cycle.
        return

    async with semaphore, lock:
        if current_generation(device_id) != generation:
            return  # deleted while we waited for the semaphore/lock

        async with session_scope() as session:
            device = await session.get(Device, device_id)
            if device is None:
                return

            try:
                live = await asyncio.to_thread(device_client.get_status, device)
            except Exception as exc:  # noqa: BLE001 -- one device's failure must not abort the cycle
                logger.warning("Unexpected error polling device %s: %s", device.name, exc)
                return

            if current_generation(device_id) != generation:
                return  # deleted while the (blocking) HTTP call was in flight

            cache = await session.get(DeviceStatusCache, device_id)
            if cache is None:
                cache = DeviceStatusCache(device_id=device_id)
                session.add(cache)

            now = datetime.now(UTC)
            previous_state = cache.state

            if live.online:
                cache.state = "online"
                cache.consecutive_failures = 0
                cache.last_success_at = now
                cache.mode = live.mode
                cache.thermostat_state = live.state
                cache.space_temp = live.space_temp
                cache.heat_temp = live.heat_temp
                cache.cool_temp = live.cool_temp
            else:
                cache.consecutive_failures += 1
                cache.last_error = live.error
                cache.last_error_at = now
                cache.state = (
                    "offline" if cache.consecutive_failures >= settings.status_offline_after_failures else "degraded"
                )

            await session.commit()
            await session.refresh(cache)

            if cache.state != previous_state or live.online:
                status_hub.broadcast(status_message(cache))


def status_message(cache: DeviceStatusCache) -> dict:
    return {
        "type": "device_status",
        "device_id": cache.device_id,
        "state": cache.state,
        "mode": cache.mode,
        "thermostat_state": cache.thermostat_state,
        "space_temp": cache.space_temp,
        "heat_temp": cache.heat_temp,
        "cool_temp": cache.cool_temp,
        "consecutive_failures": cache.consecutive_failures,
        "last_success_at": cache.last_success_at.isoformat() if cache.last_success_at else None,
        "last_error": cache.last_error,
        "last_error_at": cache.last_error_at.isoformat() if cache.last_error_at else None,
        "updated_at": cache.updated_at.isoformat() if cache.updated_at else None,
    }
