"""Database models: thermostat registry + centralized schedule entries.

Schedules live here (not on the device) because the T8900 Local API has
no remote-writable weekly-schedule endpoint -- see README for details.
The scheduler loop (heatctl/scheduler.py) reads these rows and pushes
setpoints to devices via pyvenstar at the right times.
"""

from __future__ import annotations

import enum
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Time, func
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

    # Local API credentials. NOTE: plaintext here is only acceptable
    # because this column is expected to be backed by an encrypted-at-rest
    # Postgres volume/disk in every deployment target (docker volume,
    # Azure Postgres Flexible Server). If that assumption ever changes,
    # move these behind Key Vault / envelope encryption before storing
    # real credentials -- see README "Security notes".
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password: Mapped[str | None] = mapped_column(String(128), nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    schedule_entries: Mapped[list[ScheduleEntry]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class ScheduleEntry(Base):
    """A single "at this time on these days, set these setpoints" rule."""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)

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
