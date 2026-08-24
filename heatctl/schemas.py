"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from heatctl.models import DayOfWeek


class DeviceCreate(BaseModel):
    name: str
    site: str
    host: str
    port: int = 443
    use_https: bool = True
    verify_tls: bool = False
    username: str | None = None
    password: str | None = None
    enabled: bool = True


class DeviceUpdate(BaseModel):
    name: str | None = None
    site: str | None = None
    host: str | None = None
    port: int | None = None
    use_https: bool | None = None
    verify_tls: bool | None = None
    username: str | None = None
    password: str | None = None
    enabled: bool | None = None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    site: str
    host: str
    port: int
    use_https: bool
    verify_tls: bool
    username: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Deliberately excludes `password` -- never echo credentials back.


class ScheduleEntryCreate(BaseModel):
    day_of_week: DayOfWeek
    time_of_day: time
    heat_temp: float | None = None
    cool_temp: float | None = None
    enabled: bool = True


class ScheduleEntryUpdate(BaseModel):
    day_of_week: DayOfWeek | None = None
    time_of_day: time | None = None
    heat_temp: float | None = None
    cool_temp: float | None = None
    enabled: bool | None = None


class ScheduleEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    day_of_week: DayOfWeek
    time_of_day: time
    heat_temp: float | None
    cool_temp: float | None
    enabled: bool
    last_applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeviceStatus(BaseModel):
    """Live status pulled from the device itself via pyvenstar."""

    online: bool
    error: str | None = Field(default=None)
    mode: str | None = None
    state: str | None = None
    space_temp: float | None = None
    heat_temp: float | None = None
    cool_temp: float | None = None
