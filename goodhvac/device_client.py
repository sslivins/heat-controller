"""Thin wrapper adapting DB Device rows to pyvenstar VenstarClient calls."""

from __future__ import annotations

import logging

from pyvenstar import ThermostatMode, VenstarAPIError, VenstarClient, VenstarConnectionError

from goodhvac.crypto import decrypt_password
from goodhvac.models import Device
from goodhvac.schemas import DeviceStatus

logger = logging.getLogger("goodhvac.device_client")


def client_for(device: Device) -> VenstarClient:
    return VenstarClient(
        device.host,
        port=device.port,
        use_tls=device.use_https,
        verify_tls=device.verify_tls,
        user=device.username,
        password=decrypt_password(device.password),
    )


def get_status(device: Device) -> DeviceStatus:
    """Fetch live status from a device, converting connection failures into a status flag rather than raising.

    Used by the API's device-status endpoint and the scheduler's
    pre-flight check -- callers generally want "device is unreachable"
    to be data, not an exception that aborts a whole scheduler tick or
    fleet-status page.
    """
    try:
        with client_for(device) as client:
            info = client.get_info()
            return DeviceStatus(
                online=True,
                mode=info.mode.name,
                state=info.state.name,
                space_temp=info.space_temp,
                heat_temp=info.heat_temp,
                cool_temp=info.cool_temp,
            )
    except (VenstarConnectionError, VenstarAPIError) as exc:
        logger.warning("Device %s (%s) unreachable: %s", device.name, device.host, exc)
        return DeviceStatus(online=False, error=str(exc))


def apply_setpoints(device: Device, heat_temp: float | None, cool_temp: float | None) -> None:
    """Push heat/cool setpoints to a device, filling in the missing side from current state.

    A ScheduleEntry may only set one of heat/cool (e.g. a cooling-only
    schedule); pyvenstar's set_setpoints requires both, so the current
    value is read back for whichever side wasn't specified.
    """
    with client_for(device) as client:
        info = client.get_info()
        target_heat = heat_temp if heat_temp is not None else info.heat_temp
        target_cool = cool_temp if cool_temp is not None else info.cool_temp

        # Auto mode requires cool - heat >= setpoint_delta; if the caller
        # only specified one side and the existing other side would now
        # violate that, nudge it out just enough to stay valid rather than
        # failing the whole scheduled change outright.
        if info.mode == ThermostatMode.AUTO and (target_cool - target_heat) < info.setpoint_delta:
            if heat_temp is not None and cool_temp is None:
                target_cool = target_heat + info.setpoint_delta
            elif cool_temp is not None and heat_temp is None:
                target_heat = target_cool - info.setpoint_delta

        client.set_setpoints(target_heat, target_cool)


def apply_bulk_action(
    device: Device, mode: str | None, heat_temp: float | None, cool_temp: float | None
) -> None:
    """Apply an optional mode change plus optional setpoints, for the bulk-control endpoint.

    Unlike apply_setpoints() (used by the scheduler, which only ever sets
    temperatures), this also accepts a mode string (e.g. "HEAT", "COOL",
    "OFF", "AUTO") from the bulk-apply request. Mode is applied first so
    a subsequent setpoint validation (e.g. AUTO's min delta) sees the
    target mode's constraints, not the device's previous mode.

    Raises pyvenstar's VenstarConnectionError/VenstarAPIError on failure;
    callers (the bulk-apply endpoint) are responsible for catching these
    per-device so one bad device doesn't fail the whole batch.
    """
    with client_for(device) as client:
        if mode is not None:
            client.set_mode(ThermostatMode[mode.upper()])

        if heat_temp is None and cool_temp is None:
            return

        info = client.get_info()
        target_heat = heat_temp if heat_temp is not None else info.heat_temp
        target_cool = cool_temp if cool_temp is not None else info.cool_temp

        effective_mode = ThermostatMode[mode.upper()] if mode is not None else info.mode
        if effective_mode == ThermostatMode.AUTO and (target_cool - target_heat) < info.setpoint_delta:
            if heat_temp is not None and cool_temp is None:
                target_cool = target_heat + info.setpoint_delta
            elif cool_temp is not None and heat_temp is None:
                target_heat = target_cool - info.setpoint_delta

        client.set_setpoints(target_heat, target_cool)

