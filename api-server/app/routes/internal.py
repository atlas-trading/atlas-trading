from fastapi import APIRouter

from app.routes.ws_alerts import broadcast

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/alert")
async def post_alert(payload: dict) -> dict:
    """
    Receive an alert payload from core-platform and fan it out over the
    WebSocket broadcast channel. Intended for internal-only use; not exposed
    to the public router and protected by the deploy topology (private network).
    """
    await broadcast(payload)
    return {"status": "ok"}
