"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from goodhvac.models import DayOfWeek, ValidationStatus


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str


class DeviceCreate(BaseModel):
    name: str
    site: str
    host: str
    port: int = 443
    use_https: bool = True
    verify_tls: bool = False
    username: str | None = None
    password: str | None = None
    pin: str | None = None
    enabled: bool = True
    tag_ids: list[int] = Field(default_factory=list)


class DeviceUpdate(BaseModel):
    name: str | None = None
    site: str | None = None
    host: str | None = None
    port: int | None = None
    use_https: bool | None = None
    verify_tls: bool | None = None
    username: str | None = None
    password: str | None = None
    pin: str | None = None
    enabled: bool | None = None
    tag_ids: list[int] | None = None


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
    has_pin: bool = False
    validation_status: ValidationStatus
    last_validation_error: str | None
    last_validated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tags: list[TagRead] = Field(default_factory=list)
    # Deliberately excludes `password`/`pin` -- never echo credentials back.


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


class DeviceStatusRead(BaseModel):
    """Cached status as persisted by the background poller (fast-read path)."""

    model_config = ConfigDict(from_attributes=True)

    device_id: int
    state: str  # "pending" | "online" | "degraded" | "offline"
    mode: str | None
    thermostat_state: str | None
    space_temp: float | None
    heat_temp: float | None
    cool_temp: float | None
    consecutive_failures: int
    last_success_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    updated_at: datetime


class TagCreate(BaseModel):
    key: str
    value: str


class BulkApplyRequest(BaseModel):
    device_ids: list[int]
    mode: str | None = None  # "OFF" | "HEAT" | "COOL" | "AUTO" -- forwarded as-is to pyvenstar
    heat_temp: float | None = None
    cool_temp: float | None = None


class BulkApplyResult(BaseModel):
    device_id: int
    outcome: str  # "applied" | "rejected" | "unreachable" | "timed_out" | "skipped_disabled"
    error: str | None = None


class BulkApplyResponse(BaseModel):
    results: list[BulkApplyResult]

