"""WebSocket status hub: snapshot-then-delta, coalescing, non-blocking broadcast."""

from __future__ import annotations

import asyncio

import pytest

from heatctl.ws_hub import StatusHub


class _FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent: list[dict] = []
        self._send_event = asyncio.Event()

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.sent.append(message)
        self._send_event.set()

    async def wait_for_send(self, count, timeout=1.0):
        async def _wait():
            while len(self.sent) < count:
                await asyncio.sleep(0.01)

        await asyncio.wait_for(_wait(), timeout=timeout)


@pytest.fixture
async def hub():
    h = StatusHub()
    yield h


async def test_connect_registers_client_and_accepts(hub):
    ws = _FakeWebSocket()
    await hub.connect(ws)
    assert ws.accepted
    await hub.disconnect(ws)


async def test_broadcast_delivers_to_connected_client(hub):
    ws = _FakeWebSocket()
    await hub.connect(ws)

    hub.broadcast({"type": "device_status", "device_id": 1, "state": "online"})
    await ws.wait_for_send(1)

    assert ws.sent == [{"type": "device_status", "device_id": 1, "state": "online"}]
    await hub.disconnect(ws)


async def test_broadcast_does_not_reach_disconnected_client(hub):
    ws = _FakeWebSocket()
    await hub.connect(ws)
    await hub.disconnect(ws)

    hub.broadcast({"type": "device_status", "device_id": 1, "state": "online"})
    await asyncio.sleep(0.05)

    assert ws.sent == []


async def test_send_to_delivers_snapshot_to_single_client(hub):
    ws1 = _FakeWebSocket()
    ws2 = _FakeWebSocket()
    await hub.connect(ws1)
    await hub.connect(ws2)

    await hub.send_to(ws1, {"type": "snapshot"})
    await ws1.wait_for_send(1)

    assert ws1.sent == [{"type": "snapshot"}]
    assert ws2.sent == []
    await hub.disconnect(ws1)
    await hub.disconnect(ws2)


async def test_broadcast_never_blocks_even_when_queue_full(hub):
    """broadcast() is synchronous -- verify a saturated queue doesn't raise or hang the caller."""
    ws = _FakeWebSocket()
    await hub.connect(ws)

    # Pause the sender loop's consumption by cancelling it, then flood the queue.
    client = hub._clients[ws]
    client.sender_task.cancel()
    with __import__("contextlib").suppress(asyncio.CancelledError):
        await client.sender_task

    for i in range(300):
        hub.broadcast({"type": "device_status", "device_id": i % 5, "state": "online"})

    # No exception raised, and the queue stayed within its bound.
    assert client.queue.qsize() <= 200

    await hub.disconnect(ws)


async def test_coalescing_keeps_latest_message_per_device(hub):
    ws = _FakeWebSocket()
    await hub.connect(ws)

    client = hub._clients[ws]
    client.sender_task.cancel()
    with __import__("contextlib").suppress(asyncio.CancelledError):
        await client.sender_task

    # Fill the queue with distinguishable messages all for the same device, then
    # send one more -- with coalescing, the oldest same-device entries should be
    # dropped to make room, but the newest message for that device is retained.
    for i in range(200):
        hub._enqueue_nowait(client, {"device_id": 1, "seq": i})

    hub._enqueue_nowait(client, {"device_id": 1, "seq": "newest"})

    drained = []
    while not client.queue.empty():
        drained.append(client.queue.get_nowait())

    assert drained[-1] == {"device_id": 1, "seq": "newest"}
    await hub.disconnect(ws)
