from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator

from atlas.backtest.exchange import BacktestExchange
from atlas.backtest.runner import BacktestRunner, TradeRecord
from atlas.core.exchange import Exchange
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

# ETH/USDT가 이론가(50000×0.06=3000) 대비 6.7% 과대평가 → 차익 기회
_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000.0, "ask": 50000.0, "last": 50000.0},
    "ETH/BTC": {"bid": 0.06, "ask": 0.06, "last": 0.06},
    "ETH/USDT": {"bid": 3200.0, "ask": 3200.0, "last": 3200.0},
}
_TS = datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)


class _StubFeed:
    """단일 ticker 스냅샷을 한 번 yield하는 스텁."""

    def __init__(self, tickers: dict[str, Any]):
        self._tickers = tickers

    async def stream(self, start: datetime, end: datetime) -> AsyncIterator:
        yield _TS, self._tickers


def _make_runner(tickers: dict, initial_usdt: str = "10000") -> BacktestRunner:
    exchange = BacktestExchange(
        initial_balance={
            "USDT": Decimal(initial_usdt),
            "BTC": Decimal("1"),
            "ETH": Decimal("100"),
            "BNB": Decimal("100"),
            "XRP": Decimal("10000"),
        },
        slippage=Decimal("0"),
    )
    feed = _StubFeed(tickers)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0.001"),
        min_profit=Decimal("0.001"),
    )
    risk_manager = RiskManager(
        max_order_size=Decimal("10000"),
        max_exposure=Decimal("30000"),
    )
    return BacktestRunner(
        feed=feed, exchange=exchange, strategy=strategy, risk_manager=risk_manager
    )


async def test_runner_returns_list_of_trade_records():
    runner = _make_runner(_ARB_TICKERS)
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert isinstance(records, list)


async def test_runner_produces_trade_record_on_arbitrage():
    runner = _make_runner(_ARB_TICKERS)
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert len(records) >= 1


async def test_trade_record_has_required_fields():
    runner = _make_runner(_ARB_TICKERS)
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert len(records) >= 1
    rec = records[0]
    assert isinstance(rec, TradeRecord)
    assert rec.arb_id
    assert rec.status in {"COMPLETE", "UNWIND_COMPLETE", "TIMEOUT", "FAILED"}
    assert rec.timestamp == _TS
    assert rec.leg1_pair and rec.leg2_pair and rec.leg3_pair


async def test_no_signal_no_records():
    runner = _make_runner({})
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert records == []
