from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["alerts"])

_clients: list[WebSocket] = []


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _clients.remove(websocket)


async def broadcast(message: dict) -> None:
    for client in list(_clients):
        try:
            await client.send_json(message)
        except Exception:
            _clients.discard(client)
