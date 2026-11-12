"""
WebSocket chat: /ws/chat/{conversation_id}?token=<access_token>
ConnectionManager keeps per-conversation active connections.
On message: save to DB + push to all connected clients in conversation.
Reconnect is handled client-side.
"""
import json
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Conversation, Message, Song
from api.routes.messages import create_message, _message_dict
from services.auth_service import _decode_token

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        # conversation_id -> list of (user_id, websocket)
        self._connections: Dict[str, List[tuple]] = {}

    def connect(self, conversation_id: str, user_id: str, ws: WebSocket):
        self._connections.setdefault(conversation_id, []).append((user_id, ws))

    def disconnect(self, conversation_id: str, ws: WebSocket):
        conns = self._connections.get(conversation_id, [])
        self._connections[conversation_id] = [(uid, w) for uid, w in conns if w is not ws]

    async def broadcast(self, conversation_id: str, data: dict):
        payload = json.dumps(data)
        dead = []
        for uid, ws in self._connections.get(conversation_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(conversation_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/chat/{conversation_id}")
async def ws_chat(
    conversation_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    # Authenticate via query param token
    try:
        user_id = _decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    # Verify conversation membership
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv or user_id not in (conv.user_a_id, conv.user_b_id):
        await websocket.close(code=4003)
        return

    await websocket.accept()
    manager.connect(conversation_id, user_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            content = data.get("content")
            song_id = data.get("song_id")

            if not content and not song_id:
                continue

            # Validate song ownership
            if song_id:
                song = db.query(Song).filter(Song.id == song_id, Song.user_id == user_id).first()
                if not song:
                    continue

            msg = create_message(db, conv, user_id, content, song_id)
            payload = _message_dict(msg)

            await manager.broadcast(conversation_id, payload)

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, websocket)
