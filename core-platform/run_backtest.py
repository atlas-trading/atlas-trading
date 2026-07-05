"""
백테스트 CLI.

환경 변수:
  DATABASE_URL  PostgreSQL 연결 문자열 (필수)

예시:
  # 데이터 취득 + 실행 한 번에
  DATABASE_URL=postgresql+asyncpg://... python run_backtest.py \\
    --start 2025-03-01 --end 2025-05-31 --fetch --output results.csv

  # 이미 DB에 데이터 있을 때
  DATABASE_URL=... python run_backtest.py \\
    --start 2025-03-01 --end 2025-05-31 --qty 0.001
"""

import argparse
import asyncio
import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from atlas.backtest.exchange import BacktestExchange
from atlas.backtest.feed import HistoricalFeed
from atlas.backtest.fetcher import BinanceVisionFetcher
from atlas.backtest.report import BacktestSummary, print_summary, to_csv
from atlas.backtest.runner import BacktestRunner
from atlas.backtest.store import save_run
from atlas.core.exchange import Exchange
from atlas.db.connection import create_engine, create_session_factory
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Atlas triangular arbitrage backtest")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD (inclusive)")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD (exclusive)")
    p.add_argument("--fetch", action="store_true", help="Download data before running")
    p.add_argument("--qty", default="0.001", help="Leg-1 order quantity (default: 0.001 BTC)")
    p.add_argument(
        "--initial-balance", default="1000", help="Starting USDT balance (default: 1000)"
    )
    p.add_argument("--min-profit", default="0.002", help="Min profit threshold (default: 0.2%%)")
    p.add_argument("--output", default="", help="CSV output path (optional)")
    return p.parse_args()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()

    database_url = os.environ["DATABASE_URL"]
    session_factory = create_session_factory(create_engine(database_url))

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc)

    if args.fetch:
        print(f"[FETCH] {start_date} ~ {end_date} 데이터 취득 중…")
        fetcher = BinanceVisionFetcher(session_factory)
        inserted = await fetcher.fetch(start_date, end_date)
        print(f"[FETCH] {inserted:,}행 적재 완료")

    initial_usdt = Decimal(args.initial_balance)
    slippage = Decimal("0.0005")
    exchange = BacktestExchange(
        initial_balance={
            "USDT": initial_usdt,
            "BTC": Decimal("0"),
            "ETH": Decimal("0"),
            "BNB": Decimal("0"),
            "XRP": Decimal("0"),
        },
        slippage=slippage,
    )
    feed = HistoricalFeed(session_factory)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal(args.qty),
        min_profit=Decimal(args.min_profit),
    )
    risk_manager = RiskManager(
        max_order_size=initial_usdt,
        max_exposure=initial_usdt * 3,
    )
    runner = BacktestRunner(
        feed=feed, exchange=exchange, strategy=strategy, risk_manager=risk_manager
    )

    print(f"[RUN] {start_dt.date()} ~ {end_dt.date()} 백테스트 실행 중…")
    records = await runner.run(start_dt, end_dt)

    summary = BacktestSummary(
        start=start_dt,
        end=end_dt,
        initial_balance=initial_usdt,
        final_balance=exchange.get_usdt_balance(),
        records=records,
    )
    print_summary(summary)

    try:
        run_id = await save_run(
            session_factory,
            summary,
            order_qty=Decimal(args.qty),
            min_profit=Decimal(args.min_profit),
            slippage=slippage,
        )
        print(f"결과 DB 저장됨: run_id={run_id}")
    except Exception:
        # 결과는 이미 터미널/CSV로 출력됐으므로 저장 실패로 프로세스를 죽이지 않는다
        logging.exception("백테스트 결과 DB 저장 실패")

    if args.output:
        to_csv(summary, args.output)


if __name__ == "__main__":
    asyncio.run(main())
