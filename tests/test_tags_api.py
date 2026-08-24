"""Tag CRUD + device tag assignment tests."""

from __future__ import annotations


async def test_create_and_list_tags(client):
    resp = await client.post("/tags", json={"key": "Site", "value": "HQ"})
    assert resp.status_code == 201
    body = resp.json()
    # key is normalized to lowercase; value is stripped but case preserved.
    assert body["key"] == "site"
    assert body["value"] == "HQ"

    resp = await client.get("/tags")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_create_duplicate_tag_conflicts(client):
    resp = await client.post("/tags", json={"key": "site", "value": "HQ"})
    assert resp.status_code == 201

    resp = await client.post("/tags", json={"key": "Site", "value": "HQ"})
    assert resp.status_code == 409


async def test_delete_tag(client):
    create = await client.post("/tags", json={"key": "site", "value": "HQ"})
    tag_id = create.json()["id"]

    resp = await client.delete(f"/tags/{tag_id}")
    assert resp.status_code == 204

    resp = await client.get("/tags")
    assert resp.json() == []


async def test_delete_missing_tag_404(client):
    resp = await client.delete("/tags/999")
    assert resp.status_code == 404


async def test_device_tag_assignment_roundtrip(client):
    tag = await client.post("/tags", json={"key": "site", "value": "HQ"})
    tag_id = tag.json()["id"]

    create = await client.post(
        "/devices",
        json={"name": "Office", "site": "HQ", "host": "10.0.0.1", "tag_ids": [tag_id]},
    )
    assert create.status_code == 201
    body = create.json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["id"] == tag_id

    device_id = body["id"]
    resp = await client.patch(f"/devices/{device_id}", json={"tag_ids": []})
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


async def test_device_create_unknown_tag_id_422(client):
    resp = await client.post(
        "/devices",
        json={"name": "Office", "site": "HQ", "host": "10.0.0.1", "tag_ids": [999]},
    )
    assert resp.status_code == 422
