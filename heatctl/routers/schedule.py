"""Per-device schedule-entry CRUD, nested under /devices/{device_id}/schedule."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heatctl.database import get_db
from heatctl.models import Device, ScheduleEntry
from heatctl.schemas import ScheduleEntryCreate, ScheduleEntryRead, ScheduleEntryUpdate

router = APIRouter(prefix="/devices/{device_id}/schedule", tags=["schedule"])


async def _get_device_or_404(device_id: int, db: AsyncSession) -> Device:
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("", response_model=list[ScheduleEntryRead])
async def list_schedule(device_id: int, db: AsyncSession = Depends(get_db)) -> list[ScheduleEntry]:
    await _get_device_or_404(device_id, db)
    result = await db.execute(select(ScheduleEntry).where(ScheduleEntry.device_id == device_id))
    return list(result.scalars().all())


@router.post("", response_model=ScheduleEntryRead, status_code=201)
async def create_schedule_entry(
    device_id: int, payload: ScheduleEntryCreate, db: AsyncSession = Depends(get_db)
) -> ScheduleEntry:
    await _get_device_or_404(device_id, db)
    entry = ScheduleEntry(device_id=device_id, **payload.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _get_entry_or_404(device_id: int, entry_id: int, db: AsyncSession) -> ScheduleEntry:
    entry = await db.get(ScheduleEntry, entry_id)
    if entry is None or entry.device_id != device_id:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    return entry


@router.patch("/{entry_id}", response_model=ScheduleEntryRead)
async def update_schedule_entry(
    device_id: int, entry_id: int, payload: ScheduleEntryUpdate, db: AsyncSession = Depends(get_db)
) -> ScheduleEntry:
    entry = await _get_entry_or_404(device_id, entry_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_schedule_entry(device_id: int, entry_id: int, db: AsyncSession = Depends(get_db)) -> None:
    entry = await _get_entry_or_404(device_id, entry_id, db)
    await db.delete(entry)
    await db.commit()
