import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import internal, positions, trades, ws_alerts

app = FastAPI(title="Atlas Trading Admin")

# Origins are configurable via env so deploys can lock them down to known hosts.
_origins = os.getenv("ATLAS_CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trades.router)
app.include_router(positions.router)
app.include_router(ws_alerts.router)
app.include_router(internal.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
