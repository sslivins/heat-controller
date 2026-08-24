"""Scheduler tick logic tests -- device_client calls are mocked so these
don't touch the network."""

from __future__ import annotations

from datetime import UTC, datetime, time
from unittest.mock import patch

import pytest
from sqlalchemy import select

from goodhvac import scheduler
from goodhvac.database import session_scope
from goodhvac.models import Device, ScheduleEntry


async def _make_device_with_entry(day_of_week: int, time_of_day: time, **entry_kwargs) -> tuple[int, int]:
    async with session_scope() as session:
        device = Device(name="A", site="S", host="10.0.0.1")
        session.add(device)
        await session.flush()

        entry = ScheduleEntry(device_id=device.id, day_of_week=day_of_week, time_of_day=time_of_day, **entry_kwargs)
        session.add(entry)
        await session.commit()
        return device.id, entry.id


@pytest.mark.parametrize("dummy", [None])
async def test_tick_applies_due_entry(dummy):
    now = datetime(2026, 8, 24, 9, 2, tzinfo=UTC)  # Monday == weekday() 0
    await _make_device_with_entry(now.weekday(), time(9, 0), heat_temp=68, cool_temp=75)

    with patch.object(scheduler.device_client, "apply_setpoints") as mocked:
        applied = await scheduler.tick(now)

    assert applied == 1
    mocked.assert_called_once()

    async with session_scope() as session:
        result = await session.execute(select(ScheduleEntry))
        entry = result.scalar_one()
        assert entry.last_applied_at is not None


async def test_tick_skips_entry_outside_due_window():
    now = datetime(2026, 8, 24, 9, 30, tzinfo=UTC)
    await _make_device_with_entry(now.weekday(), time(9, 0), heat_temp=68, cool_temp=75)

    with patch.object(scheduler.device_client, "apply_setpoints") as mocked:
        applied = await scheduler.tick(now)

    assert applied == 0
    mocked.assert_not_called()


async def test_tick_skips_already_applied_entry_same_day():
    now = datetime(2026, 8, 24, 9, 2, tzinfo=UTC)
    device_id, entry_id = await _make_device_with_entry(now.weekday(), time(9, 0), heat_temp=68, cool_temp=75)

    async with session_scope() as session:
        entry = await session.get(ScheduleEntry, entry_id)
        entry.last_applied_at = now
        await session.commit()

    with patch.object(scheduler.device_client, "apply_setpoints") as mocked:
        applied = await scheduler.tick(now)

    assert applied == 0
    mocked.assert_not_called()


async def test_tick_skips_disabled_entry():
    now = datetime(2026, 8, 24, 9, 2, tzinfo=UTC)
    await _make_device_with_entry(now.weekday(), time(9, 0), heat_temp=68, cool_temp=75, enabled=False)

    with patch.object(scheduler.device_client, "apply_setpoints") as mocked:
        applied = await scheduler.tick(now)

    assert applied == 0
    mocked.assert_not_called()


async def test_tick_continues_after_device_error():
    now = datetime(2026, 8, 24, 9, 2, tzinfo=UTC)
    await _make_device_with_entry(now.weekday(), time(9, 0), heat_temp=68, cool_temp=75)

    with patch.object(scheduler.device_client, "apply_setpoints", side_effect=RuntimeError("boom")):
        applied = await scheduler.tick(now)

    assert applied == 0
