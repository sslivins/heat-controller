"""Device registry CRUD + live status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heatctl import device_client
from heatctl.database import get_db
from heatctl.models import Device
from heatctl.schemas import DeviceCreate, DeviceRead, DeviceStatus, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceRead])
async def list_devices(db: AsyncSession = Depends(get_db)) -> list[Device]:
    result = await db.execute(select(Device))
    return list(result.scalars().all())


@router.post("", response_model=DeviceRead, status_code=201)
async def create_device(payload: DeviceCreate, db: AsyncSession = Depends(get_db)) -> Device:
    device = Device(**payload.model_dump())
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def _get_device_or_404(device_id: int, db: AsyncSession) -> Device:
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)) -> Device:
    return await _get_device_or_404(device_id, db)


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(device_id: int, payload: DeviceUpdate, db: AsyncSession = Depends(get_db)) -> Device:
    device = await _get_device_or_404(device_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)) -> None:
    device = await _get_device_or_404(device_id, db)
    await db.delete(device)
    await db.commit()


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(device_id: int, db: AsyncSession = Depends(get_db)) -> DeviceStatus:
    device = await _get_device_or_404(device_id, db)
    return await _run_status(device)


async def _run_status(device: Device) -> DeviceStatus:
    import asyncio

    return await asyncio.to_thread(device_client.get_status, device)
