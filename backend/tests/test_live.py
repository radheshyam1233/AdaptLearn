# tests/test_live.py
# The WebSocket live feed.
import pytest
from starlette.websockets import WebSocketDisconnect


def test_websocket_rejects_students(client, student_headers):
    token = student_headers["Authorization"].split()[1]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/dashboard?token={token}") as ws:
            ws.receive_json()


def test_tutor_receives_live_event(client, student_headers, tutor_headers, question):
    token = tutor_headers["Authorization"].split()[1]
    with client.websocket_connect(f"/ws/dashboard?token={token}") as ws:
        client.post("/attempts", json={"question_id": question.id, "selected": "A"}, headers=student_headers)
        event = ws.receive_json()
    assert event["type"] == "attempt" and event["concept"] == "Arithmetic" and event["is_correct"] is False
