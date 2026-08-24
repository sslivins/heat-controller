"""Database models: thermostat registry + centralized schedule entries.

Schedules live here (not on the device) because the T8900 Local API has
no remote-writable weekly-schedule endpoint -- see README for details.
The scheduler loop (heatctl/scheduler.py) reads these rows and pushes
setpoints to devices via pyvenstar at the right times.
"""

from __future__ import annotations

import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heatctl.database import Base


class DayOfWeek(enum.IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class ValidationStatus(enum.StrEnum):
    """Result of the most recent reachability/auth check for a device.

    Set to PENDING immediately at device creation (before any network
    call is made) so onboarding a not-yet-wired-up device never fails
    the create request itself -- validation happens afterwards, out of
    band, and only updates this field.
    """

    PENDING = "pending"
    REACHABLE = "reachable"
    AUTH_FAILED = "auth_failed"
    UNREACHABLE = "unreachable"


device_tags = Table(
    "device_tags",
    Base.metadata,
    Column("device_id", ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """A normalized key/value label, e.g. key="site" value="main-branch".

    Grouping/filtering conventions (like "site" being the default
    grouping key) are enforced at the application layer, not the schema
    -- a device may have zero or more tags with any key.
    """

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("key", "value", name="uq_tags_key_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    devices: Mapped[list[Device]] = relationship(secondary=device_tags, back_populates="tags")


class Device(Base):
    """A single registered Venstar thermostat."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    site: Mapped[str] = mapped_column(String(128), nullable=False)

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)
    use_https: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verify_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Local API credentials. Password is encrypted at rest (see
    # heatctl/crypto.py) -- the column stores a Fernet token, never
    # plaintext. Username isn't treated as secret.
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Set PENDING at creation; updated by the async post-create validation
    # check and by every subsequent status poll (see heatctl/status_poller.py).
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING
    )
    last_validation_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    schedule_entries: Mapped[list[ScheduleEntry]] = relationship(
        back_populates="device", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list[Tag]] = relationship(secondary=device_tags, back_populates="devices")
    status: Mapped[DeviceStatusCache | None] = relationship(
        back_populates="device", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class ScheduleEntry(Base):
    """A single "at this time on these days, set these setpoints" rule."""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)

    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek), nullable=False)
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)

    heat_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cool_temp: Mapped[float | None] = mapped_column(Float, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Guards against re-applying the same entry twice within one
    # scheduler tick if the loop is slow or restarts mid-minute.
    last_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="schedule_entries")


class DeviceStatusCache(Base):
    """Latest known live status for a device, persisted so a restart

    shows "stale since <time>" instead of falsely "online". Upserted by
    the background status poller; read by the API/WebSocket layer as
    the fast-path source of truth (avoids hitting the device on every
    dashboard page load).
    """

    __tablename__ = "device_status_cache"

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)

    # online: last poll succeeded. degraded: 1-2 consecutive failures.
    # offline: >= settings.status_offline_after_failures consecutive
    # failures. Three states (not a bool) to avoid flapping the UI red
    # on a single dropped poll.
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    thermostat_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    space_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cool_temp: Mapped[float | None] = mapped_column(Float, nullable=True)

    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="status")

