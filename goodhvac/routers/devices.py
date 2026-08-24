"""Device registry CRUD + live status endpoint + bulk control."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from goodhvac import device_client
from goodhvac.config import settings
from goodhvac.crypto import encrypt_password
from goodhvac.database import get_db, session_scope
from goodhvac.device_locks import bump_generation, forget, lock_for
from goodhvac.models import Device, Tag, ValidationStatus
from goodhvac.schemas import (
    BulkApplyRequest,
    BulkApplyResponse,
    BulkApplyResult,
    DeviceCreate,
    DeviceRead,
    DeviceStatus,
    DeviceUpdate,
)

logger = logging.getLogger("goodhvac.routers.devices")

router = APIRouter(prefix="/devices", tags=["devices"])


async def _load_tags(db: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = list(result.scalars().all())
    missing = set(tag_ids) - {t.id for t in tags}
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown tag ids: {sorted(missing)}")
    return tags


@router.get("", response_model=list[DeviceRead])
async def list_devices(db: AsyncSession = Depends(get_db)) -> list[Device]:
    result = await db.execute(select(Device).options(selectinload(Device.tags)))
    return list(result.scalars().all())


@router.post("", response_model=DeviceRead, status_code=201)
async def create_device(payload: DeviceCreate, db: AsyncSession = Depends(get_db)) -> Device:
    data = payload.model_dump(exclude={"tag_ids", "password"})
    device = Device(**data, password=encrypt_password(payload.password))
    device.tags = await _load_tags(db, payload.tag_ids)
    # validation_status defaults to PENDING at the model level -- a device
    # that isn't wired up / reachable yet is still created successfully.
    # See _validate_device_async below for how it gets updated.
    db.add(device)
    await db.commit()
    await db.refresh(device)
    await db.refresh(device, attribute_names=["tags"])

    # Fire-and-forget: don't make device creation wait on a network round
    # trip to a thermostat that might not even be plugged in yet.
    await _maybe_validate_async(device.id)

    return device


async def _maybe_validate_async(device_id: int) -> None:
    if not settings.disable_async_validation:
        asyncio.create_task(_validate_device_async(device_id))


async def _validate_device_async(device_id: int) -> None:
    """Check reachability/auth for a newly created (or re-validated) device, out of band."""
    async with session_scope() as session:
        device = await session.get(Device, device_id)
        if device is None:
            return

        try:
            status = await asyncio.to_thread(device_client.get_status, device)
        except Exception as exc:  # noqa: BLE001 -- validation must never raise into the caller
            logger.warning("Device validation crashed for %s: %s", device.name, exc)
            device.validation_status = ValidationStatus.UNREACHABLE
            device.last_validation_error = str(exc)
        else:
            if status.online:
                device.validation_status = ValidationStatus.REACHABLE
                device.last_validation_error = None
            elif status.error and "401" in status.error:
                device.validation_status = ValidationStatus.AUTH_FAILED
                device.last_validation_error = status.error
            else:
                device.validation_status = ValidationStatus.UNREACHABLE
                device.last_validation_error = status.error

        device.last_validated_at = datetime.now(UTC)
        await session.commit()


async def _get_device_or_404(device_id: int, db: AsyncSession) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id).options(selectinload(Device.tags)))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)) -> Device:
    return await _get_device_or_404(device_id, db)


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(device_id: int, payload: DeviceUpdate, db: AsyncSession = Depends(get_db)) -> Device:
    device = await _get_device_or_404(device_id, db)
    updates = payload.model_dump(exclude_unset=True, exclude={"tag_ids", "password"})
    for field, value in updates.items():
        setattr(device, field, value)

    if "password" in payload.model_fields_set:
        device.password = encrypt_password(payload.password)

    if payload.tag_ids is not None:
        device.tags = await _load_tags(db, payload.tag_ids)

    await db.commit()
    await db.refresh(device)
    await db.refresh(device, attribute_names=["tags"])

    # Credentials/host changed -- re-validate so validation_status doesn't
    # keep showing a stale result from before the edit.
    if {"host", "port", "use_https", "verify_tls", "username", "password"} & payload.model_fields_set:
        await _maybe_validate_async(device.id)

    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)) -> None:
    device = await _get_device_or_404(device_id, db)

    # Bump the generation *before* deleting so any poll/apply already in
    # flight for this device discards its result instead of writing back
    # to (or broadcasting for) a device that's about to be gone. The
    # in-memory lock/generation bookkeeping is dropped after the DB row
    # is actually removed to avoid a tiny window where a new poll cycle
    # could recreate an entry for an id no longer in the DB.
    bump_generation(device_id)

    async with lock_for(device_id):
        await db.delete(device)  # ON DELETE CASCADE removes schedule_entries, device_tags, status_cache rows
        await db.commit()

    forget(device_id)


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(device_id: int, db: AsyncSession = Depends(get_db)) -> DeviceStatus:
    device = await _get_device_or_404(device_id, db)
    return await asyncio.to_thread(device_client.get_status, device)


@router.post("/bulk-apply", response_model=BulkApplyResponse)
async def bulk_apply(payload: BulkApplyRequest, db: AsyncSession = Depends(get_db)) -> BulkApplyResponse:
    """Apply a mode/setpoint change to many devices in parallel.

    Always attempts every enabled selected device live (cached "offline"
    status is advisory only and may be stale -- see design notes in
    goodhvac/status_poller.py) and reports per-device outcomes rather
    than failing the whole request if some devices are unreachable.
    """
    result = await db.execute(select(Device).where(Device.id.in_(payload.device_ids)))
    devices = {d.id: d for d in result.scalars().all()}

    async def _apply_one(device_id: int) -> BulkApplyResult:
        device = devices.get(device_id)
        if device is None:
            return BulkApplyResult(device_id=device_id, outcome="rejected", error="Device not found")
        if not device.enabled:
            return BulkApplyResult(device_id=device_id, outcome="skipped_disabled")

        try:
            async with lock_for(device_id):
                await asyncio.wait_for(
                    asyncio.to_thread(
                        device_client.apply_bulk_action, device, payload.mode, payload.heat_temp, payload.cool_temp
                    ),
                    timeout=15.0,
                )
            return BulkApplyResult(device_id=device_id, outcome="applied")
        except TimeoutError:
            return BulkApplyResult(device_id=device_id, outcome="timed_out")
        except Exception as exc:  # noqa: BLE001 -- classify as unreachable/rejected for the caller, per-device
            message = str(exc)
            outcome = "unreachable" if "Connection" in type(exc).__name__ else "rejected"
            return BulkApplyResult(device_id=device_id, outcome=outcome, error=message)

    semaphore = asyncio.Semaphore(10)

    async def _bounded(device_id: int) -> BulkApplyResult:
        async with semaphore:
            return await _apply_one(device_id)

    results = await asyncio.gather(*(_bounded(device_id) for device_id in payload.device_ids))
    return BulkApplyResponse(results=list(results))

