"""WebSocket broadcast hub for live device status updates.

Design notes (see session design review):
- The poller never awaits a browser's send directly. It calls
  ``broadcast()``, which only enqueues onto each client's bounded
  queue -- a slow/stalled tab can't block the poller or other clients.
- Each client has a dedicated sender task draining its own queue.
- Queue is bounded and coalescing: if a client falls behind, we drop
  the oldest queued message for a given device_id and keep only the
  latest (status updates are naturally idempotent snapshots, so this
  is safe -- no ordering/business logic depends on intermediate
  states).
- On connect, a client is registered *before* the initial snapshot is
  read (see routers/ws.py), so no update can be missed between
  "snapshot taken" and "subscribed" -- any update racing the snapshot
  either lands in the snapshot itself or in the queue right after.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("goodhvac.ws_hub")

_QUEUE_MAXSIZE = 200


@dataclass
class _Client:
    websocket: WebSocket
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=lambda: asyncio.Queue(maxsize=_QUEUE_MAXSIZE))
    sender_task: asyncio.Task | None = None


class StatusHub:
    def __init__(self) -> None:
        self._clients: dict[WebSocket, _Client] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        client = _Client(websocket=websocket)
        client.sender_task = asyncio.create_task(self._sender_loop(client))
        self._clients[websocket] = client

    async def disconnect(self, websocket: WebSocket) -> None:
        client = self._clients.pop(websocket, None)
        if client and client.sender_task:
            client.sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await client.sender_task

    async def send_to(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a one-off message (e.g. the initial full snapshot) to a single just-connected client."""
        client = self._clients.get(websocket)
        if client is not None:
            await self._enqueue(client, message)

    def broadcast(self, message: dict[str, Any]) -> None:
        """Fan a status update out to all connected clients. Never awaits -- safe to call from the poller loop."""
        for client in list(self._clients.values()):
            self._enqueue_nowait(client, message)

    def _enqueue_nowait(self, client: _Client, message: dict[str, Any]) -> None:
        try:
            client.queue.put_nowait(message)
        except asyncio.QueueFull:
            self._coalesce_and_retry(client, message)

    async def _enqueue(self, client: _Client, message: dict[str, Any]) -> None:
        try:
            client.queue.put_nowait(message)
        except asyncio.QueueFull:
            self._coalesce_and_retry(client, message)

    def _coalesce_and_retry(self, client: _Client, message: dict[str, Any]) -> None:
        """Drop the oldest same-device update to make room, rather than blocking or dropping the newest."""
        device_id = message.get("device_id")
        try:
            drained: list[dict[str, Any]] = []
            while not client.queue.empty():
                drained.append(client.queue.get_nowait())
            kept = [m for m in drained if not (device_id is not None and m.get("device_id") == device_id)]
            for m in kept[-(_QUEUE_MAXSIZE - 1) :]:
                client.queue.put_nowait(m)
            client.queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("WS client queue saturated even after coalescing; dropping message")

    async def _sender_loop(self, client: _Client) -> None:
        try:
            while True:
                message = await client.queue.get()
                await client.websocket.send_json(message)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 -- any send failure just ends this client's loop
            logger.info("WS client sender loop ending (disconnected)")


status_hub = StatusHub()
