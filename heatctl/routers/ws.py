"""WebSocket endpoint pushing live device status to connected browser tabs."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from heatctl.database import session_scope
from heatctl.models import DeviceStatusCache
from heatctl.status_poller import status_message
from heatctl.ws_hub import status_hub

router = APIRouter(tags=["status"])


@router.websocket("/ws/status")
async def ws_status(websocket: WebSocket) -> None:
    # Register with the hub *before* reading the snapshot, so any update
    # that races the snapshot read lands in this client's queue rather
    # than being missed entirely.
    await status_hub.connect(websocket)
    try:
        async with session_scope() as session:
            result = await session.execute(select(DeviceStatusCache))
            snapshot = [status_message(cache) for cache in result.scalars().all()]
        await status_hub.send_to(websocket, {"type": "snapshot", "devices": snapshot})

        while True:
            # Clients don't send anything meaningful; just keep the
            # connection open and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await status_hub.disconnect(websocket)
