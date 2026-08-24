"""device_client tests using requests-mock against a fake T8900 endpoint."""

from __future__ import annotations

import pytest

from heatctl.device_client import apply_setpoints, get_status
from heatctl.models import Device


def _device(**overrides) -> Device:
    defaults = dict(id=1, name="A", site="S", host="192.168.1.149", port=443, use_https=True, verify_tls=False)
    defaults.update(overrides)
    return Device(**defaults)


INFO_PAYLOAD = {
    "name": "T8900",
    "mode": 1,
    "state": 1,
    "fan": 0,
    "fanstate": 0,
    "spacetemp": 70.0,
    "heattemp": 68.0,
    "cooltemp": 75.0,
    "heattempmin": 40.0,
    "heattempmax": 99.0,
    "cooltempmin": 40.0,
    "cooltempmax": 99.0,
    "setpointdelta": 2,
    "away": 0,
    "schedule": 0,
}
ROOT_PAYLOAD = {"api_ver": 9, "type": "commercial", "model": "COLORTOUCH", "firmware": "6.93"}


@pytest.fixture
def mock_device(requests_mock):
    requests_mock.get("https://192.168.1.149:443/", json=ROOT_PAYLOAD)
    requests_mock.get("https://192.168.1.149:443/query/info", json=INFO_PAYLOAD)
    requests_mock.post("https://192.168.1.149:443/control", json={"success": True})
    return requests_mock


def test_get_status_online(mock_device):
    status = get_status(_device())
    assert status.online is True
    assert status.space_temp == 70.0


def test_get_status_unreachable():
    status = get_status(_device(host="203.0.113.1", port=1))
    assert status.online is False
    assert status.error


def test_apply_setpoints_fills_missing_side(mock_device):
    apply_setpoints(_device(), heat_temp=69, cool_temp=None)

    control_request = [r for r in mock_device.request_history if r.path == "/control"][0]
    assert "heattemp=69" in control_request.text
    assert "cooltemp=75" in control_request.text


def test_apply_bulk_action_mode_only(mock_device):
    from heatctl.device_client import apply_bulk_action

    apply_bulk_action(_device(), mode="HEAT", heat_temp=None, cool_temp=None)

    control_requests = [r for r in mock_device.request_history if r.path == "/control"]
    assert len(control_requests) == 1
    assert "mode=1" in control_requests[0].text


def test_apply_bulk_action_mode_and_setpoints(mock_device):
    from heatctl.device_client import apply_bulk_action

    apply_bulk_action(_device(), mode="HEAT", heat_temp=69, cool_temp=None)

    control_requests = [r for r in mock_device.request_history if r.path == "/control"]
    # First request sets mode (echoing back current setpoints unchanged),
    # second request applies the new heat setpoint.
    assert len(control_requests) == 2
    assert "mode=1" in control_requests[0].text
    assert "heattemp=69" in control_requests[1].text
    assert "cooltemp=75" in control_requests[1].text


def test_apply_bulk_action_no_mode_no_setpoints_is_noop(mock_device):
    from heatctl.device_client import apply_bulk_action

    apply_bulk_action(_device(), mode=None, heat_temp=None, cool_temp=None)

    control_requests = [r for r in mock_device.request_history if r.path == "/control"]
    assert control_requests == []
