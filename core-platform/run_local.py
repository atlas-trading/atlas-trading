"""
로컬 Binance 테스트넷 실행 스크립트.

환경 변수:
  BINANCE_TESTNET_API_KEY    — Binance testnet API key
  BINANCE_TESTNET_API_SECRET — Binance testnet API secret
  DATABASE_URL               — (선택) PostgreSQL URL (예: postgresql+asyncpg://atlas:atlas@localhost:5432/atlas)
  DISCORD_WEBHOOK            — (선택) Discord webhook URL
  VERBOSE                    — "1" 이면 틱·신호·체결 로그 출력 (기본 "1")

실행:
  BINANCE_TESTNET_API_KEY=... BINANCE_TESTNET_API_SECRET=... \
    DATABASE_URL=... uv run python run_local.py
"""

import asyncio
import os
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.events.bus import EventBus
from atlas.exchange.binance import BinanceAdapter
from atlas.execution.engine import ExecutionEngine
from atlas.execution.state import ArbitrageStateMachine
from atlas.live.runner import LiveRunner
from atlas.market.feed import MarketDataFeed
from atlas.outbox.queue import OutboxQueue
from atlas.outbox.workers import AlertWorker
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

VERBOSE = os.environ.get("VERBOSE", "1") == "1"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# 레그당 주문량 (BTC 기준 소수점). 테스트넷이라 0.001 BTC ≈ $50 수준으로 설정
ORDER_QUANTITY = Decimal(os.environ.get("ORDER_QUANTITY", "0.001"))
MIN_PROFIT = Decimal(os.environ.get("MIN_PROFIT", "0.005"))  # 0.5% — 수수료 손익분기 이상


async def main() -> None:
    api_key = os.environ["BINANCE_TESTNET_API_KEY"]
    api_secret = os.environ["BINANCE_TESTNET_API_SECRET"]

    tick_queue: asyncio.Queue = asyncio.Queue()
    alert_queue: OutboxQueue = asyncio.Queue()
    bus = EventBus()

    session_factory = None
    if DATABASE_URL:
        from atlas.db.connection import create_engine, create_session_factory

        session_factory = create_session_factory(create_engine(DATABASE_URL))
        print(f"[DB] 연결됨: {DATABASE_URL.split('@')[-1]}")

    adapter = BinanceAdapter(api_key=api_key, api_secret=api_secret, testnet=True)

    feed = MarketDataFeed(exchange=Exchange.BINANCE, bus=bus, tick_queue=tick_queue)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=ORDER_QUANTITY,
        min_profit=MIN_PROFIT,
    )
    state_machine = ArbitrageStateMachine(
        exchange=adapter, verbose=VERBOSE, session_factory=session_factory
    )
    # USDT notional caps. 0.001 BTC ≈ $50 → per-leg cap $200 keeps test orders snug.
    risk_manager = RiskManager(
        max_order_size=Decimal("200"),
        max_exposure=Decimal("600"),
    )
    engine = ExecutionEngine(risk_manager=risk_manager, state_machine=state_machine)
    runner = LiveRunner(
        exchange=adapter,
        feed=feed,
        strategy=strategy,
        engine=engine,
        verbose=VERBOSE,
    )

    workers = []
    if DISCORD_WEBHOOK:
        workers.append(
            asyncio.create_task(AlertWorker(queue=alert_queue, webhook_url=DISCORD_WEBHOOK).run())
        )

    pairs = strategy.all_pairs()
    print("[START] Atlas Trading — Binance Testnet")
    print(
        f"[CONFIG] qty={ORDER_QUANTITY} min_profit={float(MIN_PROFIT) * 100:.1f}% verbose={VERBOSE}"
    )
    print(f"[PAIRS] {[f'{p.ticker}/{p.quote}' for p in pairs]}")
    print("─" * 60)

    try:
        await runner.run()
    except KeyboardInterrupt:
        pass
    finally:
        for w in workers:
            w.cancel()
        await adapter.close()
        print("\n[STOP] 종료")


if __name__ == "__main__":
    asyncio.run(main())
