"""
Tests for the alerts wiring: WebSocket broadcast hygiene and the
/internal/alert HTTP fan-out endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.routes import ws_alerts

client = TestClient(app)


def test_clients_is_a_set() -> None:
    # C-4 bug: list.discard() does not exist, so the broadcast cleanup raised
    # AttributeError. Switching the registry to a set fixes that.
    assert isinstance(ws_alerts._clients, set)


def test_ws_alerts_round_trip() -> None:
    # Open a WS, then POST an alert to /internal/alert and confirm the client
    # receives it via the broadcast path.
    with client.websocket_connect("/ws/alerts") as ws:
        payload = {"type": "COMPLETE", "arb_id": "abc123", "pnl": "1.23"}
        response = client.post("/internal/alert", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        message = ws.receive_json()
        assert message == payload


def test_internal_alert_with_no_clients_succeeds() -> None:
    # Posting when no WS clients are connected must still return 200.
    response = client.post("/internal/alert", json={"type": "COMPLETE"})
    assert response.status_code == 200
