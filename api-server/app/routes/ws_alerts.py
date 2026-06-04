from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["alerts"])

_clients: set[WebSocket] = set()


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _clients.discard(websocket)


async def broadcast(message: dict) -> None:
    # Snapshot to avoid mutation during iteration when a send fails.
    for client in list(_clients):
        try:
            await client.send_json(message)
        except Exception:
            _clients.discard(client)
