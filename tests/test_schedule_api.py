"""Schedule-entry CRUD tests."""

from __future__ import annotations


async def _make_device(client) -> int:
    resp = await client.post("/devices", json={"name": "A", "site": "S", "host": "10.0.0.1"})
    return resp.json()["id"]


async def test_create_and_list_schedule_entry(client):
    device_id = await _make_device(client)

    resp = await client.post(
        f"/devices/{device_id}/schedule",
        json={"day_of_week": 0, "time_of_day": "09:00:00", "heat_temp": 68, "cool_temp": 75},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["heat_temp"] == 68
    assert body["device_id"] == device_id

    resp = await client.get(f"/devices/{device_id}/schedule")
    assert len(resp.json()) == 1


async def test_schedule_entry_requires_valid_device(client):
    resp = await client.post(
        "/devices/999/schedule",
        json={"day_of_week": 0, "time_of_day": "09:00:00"},
    )
    assert resp.status_code == 404


async def test_update_and_delete_schedule_entry(client):
    device_id = await _make_device(client)
    create = await client.post(
        f"/devices/{device_id}/schedule", json={"day_of_week": 0, "time_of_day": "09:00:00", "heat_temp": 68}
    )
    entry_id = create.json()["id"]

    resp = await client.patch(f"/devices/{device_id}/schedule/{entry_id}", json={"heat_temp": 70})
    assert resp.status_code == 200
    assert resp.json()["heat_temp"] == 70

    resp = await client.delete(f"/devices/{device_id}/schedule/{entry_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/devices/{device_id}/schedule")
    assert resp.json() == []
