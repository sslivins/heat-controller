"""Per-device coordination primitives shared by the poller, scheduler, and bulk-apply.

A single asyncio.Lock per device id ensures the background status
poller and any write operation (scheduled apply, bulk apply) never talk
to the same physical thermostat concurrently -- pyvenstar's HTTP/digest
session isn't safe to share across concurrent calls, and overlapping
reads/writes could otherwise race on the device itself.

Also tracks a per-device "generation" counter, bumped when a device is
deleted. Any in-flight poll/apply that started against an older
generation discards its result instead of writing back stale data for
a device that no longer exists (or was re-created reusing the same id,
which doesn't happen with a serial primary key, but the check is cheap
and removes the class of bug entirely).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
_generations: dict[int, int] = defaultdict(int)


def lock_for(device_id: int) -> asyncio.Lock:
    return _locks[device_id]


def current_generation(device_id: int) -> int:
    return _generations[device_id]


def bump_generation(device_id: int) -> None:
    """Call when a device is deleted, to invalidate any in-flight work."""
    _generations[device_id] += 1


def forget(device_id: int) -> None:
    """Drop bookkeeping for a deleted device (avoids unbounded growth over the app's lifetime)."""
    _locks.pop(device_id, None)
    _generations.pop(device_id, None)
