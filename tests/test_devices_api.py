"""Device registry CRUD tests."""

from __future__ import annotations


async def test_create_and_list_device(client):
    resp = await client.post(
        "/devices",
        json={"name": "Office", "site": "HQ", "host": "192.168.1.149", "port": 443, "use_https": True},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Office"
    assert "password" not in body

    resp = await client.get("/devices")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_device_404(client):
    resp = await client.get("/devices/999")
    assert resp.status_code == 404


async def test_update_device(client):
    create = await client.post("/devices", json={"name": "A", "site": "S", "host": "10.0.0.1"})
    device_id = create.json()["id"]

    resp = await client.patch(f"/devices/{device_id}", json={"name": "B"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"


async def test_delete_device(client):
    create = await client.post("/devices", json={"name": "A", "site": "S", "host": "10.0.0.1"})
    device_id = create.json()["id"]

    resp = await client.delete(f"/devices/{device_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/devices/{device_id}")
    assert resp.status_code == 404


async def test_device_status_unreachable(client):
    create = await client.post("/devices", json={"name": "A", "site": "S", "host": "192.0.2.1", "port": 1})
    device_id = create.json()["id"]

    resp = await client.get(f"/devices/{device_id}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["online"] is False
    assert body["error"]
