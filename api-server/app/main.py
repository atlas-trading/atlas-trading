"""FastAPI Application Entry Point"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1 import backtests, strategies, parameter_optimization, market

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

# Gzip compression middleware (70-80% size reduction)
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

app.include_router(
    market.router,
    prefix=f"{settings.api_prefix}/market",
    tags=["market"],
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
        from app.strategies.statistical_arbitrage import StatisticalArbitrageStrategy
        from app.strategies.ict_smart_money import ICTSmartMoneyStrategy
        from app.strategies.market_microstructure import MarketMicrostructureStrategy
        from app.strategies.adaptive_grid_trading import AdaptiveGridTradingStrategy
        from app.strategies.triangular_arbitrage import TriangularArbitrageStrategy

        # 프로 전략 등록
        strategies = [
            StatisticalArbitrageStrategy,
            ICTSmartMoneyStrategy,
            MarketMicrostructureStrategy,
            AdaptiveGridTradingStrategy,
            TriangularArbitrageStrategy,
        ]

        for strategy_class in strategies:
            register_strategy(strategy_class)

        print(f"[Startup] ✓ Registered {len(strategies)} professional strategies:")
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
