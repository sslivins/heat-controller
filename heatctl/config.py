"""Application configuration, loaded from environment variables.

Mirrors agora-cms's pattern of a single pydantic-settings ``Settings``
object with an ``HEATCTL_`` prefix, constructed once and imported
wherever needed.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEATCTL_", env_file=".env", extra="ignore")

    # Postgres in docker-compose / Azure Postgres Flexible Server in prod.
    # Falls back to a local SQLite file so tests and quick local runs don't
    # require a running Postgres instance.
    database_url: str = "sqlite+aiosqlite:///./heatctl.db"

    # How often (seconds) the scheduler loop wakes up to check for due
    # schedule entries. 60s is fine for a fleet of ~50 devices checked
    # against minute-granularity schedules.
    scheduler_interval_seconds: int = 60

    # Default TLS verification for device HTTP(S) calls. Most T8900 units
    # on the Local API present a self-signed cert, so this defaults False;
    # override per-device once real certs are in play.
    device_verify_tls: bool = False

    # Default HTTP timeout (seconds) for device API calls.
    device_timeout_seconds: float = 10.0


settings = Settings()
