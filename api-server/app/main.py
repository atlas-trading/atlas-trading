"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import backtests

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    backtests.router,
    prefix=f"{settings.api_prefix}/backtests",
    tags=["backtests"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Atlas Trading API",
        "version": settings.api_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
