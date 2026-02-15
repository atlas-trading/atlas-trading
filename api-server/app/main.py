"""FastAPI Application Entry Point"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1 import backtests, strategies

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

app.include_router(
    strategies.router,
    prefix=f"{settings.api_prefix}/strategies",
    tags=["strategies"],
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


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화 작업"""
    # 전략 레지스트리 초기화
    from app.api.v1.strategies import register_strategy

    # core-platform의 전략들을 동적으로 import하고 등록
    import sys
    from pathlib import Path

    # core-platform 경로 추가
    core_platform_path = Path(__file__).parent.parent.parent / "core-platform"
    if str(core_platform_path) not in sys.path:
        sys.path.insert(0, str(core_platform_path))

    try:
        # 전략 import 및 등록
        from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
        from app.strategies.golden_cross import GoldenCrossStrategy
        from app.strategies.rsi_strategy import RSIStrategy

        register_strategy(RSIMeanReversionStrategy)
        register_strategy(GoldenCrossStrategy)
        register_strategy(RSIStrategy)

        print(f"[Startup] Registered {len([RSIMeanReversionStrategy, GoldenCrossStrategy, RSIStrategy])} strategies")
    except Exception as e:
        print(f"[Startup] Error registering strategies: {e}")
        import traceback
        traceback.print_exc()


# Mount static files (HTML visualization)
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
