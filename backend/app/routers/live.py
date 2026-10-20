# app/routers/live.py
# WebSocket endpoint for the tutor dashboard's live feed.

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_user_from_token
from ..services.realtime import manager

router = APIRouter(tags=["live"])


@router.websocket("/ws/dashboard")
async def dashboard_feed(websocket: WebSocket, token: str = "", db: Session = Depends(get_db)):
    # Browsers can't send an Authorization header when opening a WebSocket,
    # so the JWT comes in the URL: /ws/dashboard?token=...
    user = get_user_from_token(token, db)
    # Give the database connection back NOW: this socket may stay open for hours
    db.close()
    if user is None or user.role != "tutor":
        # 1008 = "policy violation": close without accepting
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from the tutor; waiting here keeps the
            # connection open and tells us when the browser disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
