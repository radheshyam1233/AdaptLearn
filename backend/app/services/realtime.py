# app/services/realtime.py
# Keeps track of tutors connected over WebSocket and pushes events to all of them.
# Limitation (good to mention in interviews): this list lives in ONE server
# process. With several servers you'd fan out through Redis Pub/Sub.

import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, event: dict) -> None:
        """Send to every tutor; drop connections that have died."""
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
