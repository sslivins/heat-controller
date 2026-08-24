"""Application configuration, loaded from environment variables.

Mirrors agora-cms's pattern of a single pydantic-settings ``Settings``
object with an ``GOODHVAC_`` prefix, constructed once and imported
wherever needed.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOODHVAC_", env_file=".env", extra="ignore")

    # Postgres in docker-compose / Azure Postgres Flexible Server in prod.
    # Falls back to a local SQLite file so tests and quick local runs don't
    # require a running Postgres instance.
    database_url: str = "sqlite+aiosqlite:///./goodhvac.db"

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

    # Status poller: how often (seconds) each device is polled, and the
    # max number of devices polled concurrently (keeps LAN/event-loop load
    # bounded regardless of fleet size).
    status_poll_interval_seconds: float = 20.0
    status_poll_concurrency: int = 10
    # Consecutive failed polls before a device flips from "degraded" to
    # "offline" in the UI -- avoids flagging a device red on one dropped
    # packet.
    status_offline_after_failures: int = 3

    # Fernet key (44-char urlsafe-base64 string from cryptography.fernet.Fernet.generate_key())
    # used to encrypt device passwords at rest. Required in production;
    # a fixed dev-only key is used as a fallback so tests/local runs work
    # without extra setup.
    credential_encryption_key: str = "kkMGGskqapgFSDE0Mamz0VoB6ZCW3Xk-s4ATRNkRVUE="

    # Disables the fire-and-forget post-create/update device validation
    # task. Off by default in production; the test suite sets this True
    # so tests don't spawn real background network calls against a
    # per-test SQLite engine/event loop that's already torn down by the
    # time the task would run.
    disable_async_validation: bool = False


settings = Settings()
