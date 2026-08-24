"""Centralized scheduler: periodically applies due ScheduleEntry rows to devices.

Runs as its own asyncio task (started from heatctl.main's lifespan), since
the T8900 Local API has no remote-writable weekly schedule of its own --
see README "Why is scheduling centralized?".
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from heatctl import device_client
from heatctl.config import settings
from heatctl.database import session_scope
from heatctl.device_locks import lock_for
from heatctl.models import DayOfWeek, Device, ScheduleEntry

logger = logging.getLogger("heatctl.scheduler")

# An entry is only "due" within this window of its scheduled time, so a
# slow tick or brief scheduler downtime doesn't cause it to fire hours
# late, and a fast tick doesn't double-apply it (guarded separately by
# last_applied_at).
_DUE_WINDOW = timedelta(minutes=5)


async def run_forever() -> None:
    logger.info("Scheduler starting, tick interval=%ss", settings.scheduler_interval_seconds)
    while True:
        try:
            await tick()
        except Exception:  # noqa: BLE001 -- one bad tick must never kill the loop
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(settings.scheduler_interval_seconds)


async def tick(now: datetime | None = None) -> int:
    """Run one scheduler pass. Returns the number of entries applied. Exposed for tests."""
    now = now or datetime.now(UTC)
    applied = 0

    async with session_scope() as session:
        result = await session.execute(
            select(ScheduleEntry).join(Device).where(
                ScheduleEntry.enabled.is_(True),
                Device.enabled.is_(True),
                ScheduleEntry.day_of_week == DayOfWeek(now.weekday()),
            )
        )
        entries = result.scalars().all()

        for entry in entries:
            if _already_applied_today(entry, now):
                continue
            if not _is_due(entry, now):
                continue

            device = await session.get(Device, entry.device_id)
            if device is None:
                continue

            try:
                async with lock_for(device.id):
                    await asyncio.to_thread(device_client.apply_setpoints, device, entry.heat_temp, entry.cool_temp)
            except Exception as exc:  # noqa: BLE001 -- log and continue with other entries
                logger.warning(
                    "Failed to apply schedule entry %s to device %s: %s", entry.id, device.name, exc
                )
                continue

            entry.last_applied_at = now
            applied += 1

        if applied:
            await session.commit()

    return applied


def _is_due(entry: ScheduleEntry, now: datetime) -> bool:
    scheduled = now.replace(
        hour=entry.time_of_day.hour, minute=entry.time_of_day.minute, second=0, microsecond=0
    )
    return scheduled <= now <= scheduled + _DUE_WINDOW


def _already_applied_today(entry: ScheduleEntry, now: datetime) -> bool:
    return entry.last_applied_at is not None and entry.last_applied_at.date() == now.date()
