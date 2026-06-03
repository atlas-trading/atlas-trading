from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import positions, trades, ws_alerts

app = FastAPI(title="Atlas Trading Admin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trades.router)
app.include_router(positions.router)
app.include_router(ws_alerts.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
