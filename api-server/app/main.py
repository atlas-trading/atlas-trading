"""FastAPI Application Entry Point"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1 import backtests, strategies, parameter_optimization

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

app.include_router(
    parameter_optimization.router,
    prefix=f"{settings.api_prefix}",
    tags=["optimization"],
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
    try:
        # 전략 import 및 등록 (strategies는 core-platform으로 심볼릭 링크됨)
        from app.api.v1.strategies import register_strategy
        from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
        from app.strategies.funding_rate_arbitrage import FundingRateArbitrageStrategy
        from app.strategies.pairs_trading import PairsTradingStrategy
        from app.strategies.trend_following import TrendFollowingStrategy
        from app.strategies.breakout import BreakoutStrategy

        # 전략 등록
        strategies = [
            RSIMeanReversionStrategy,
            FundingRateArbitrageStrategy,
            PairsTradingStrategy,
            TrendFollowingStrategy,
            BreakoutStrategy
        ]

        for strategy_class in strategies:
            register_strategy(strategy_class)

        print(f"[Startup] ✓ Registered {len(strategies)} strategies:")
        for strategy_class in strategies:
            print(f"  - {strategy_class.__name__}")

    except Exception as e:
        print(f"[Startup] ✗ Error registering strategies: {e}")
        import traceback
        traceback.print_exc()


# Mount static files (HTML visualization)
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
