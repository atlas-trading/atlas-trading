import asyncio
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.events.bus import EventBus
from atlas.exchange.exchange_interface import ExchangeInterface
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.balance import Balance
from atlas.execution.engine import ExecutionEngine
from atlas.execution.order import Order
from atlas.live.runner import LiveRunner
from atlas.market.feed import MarketDataFeed
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

# arb-triggering prices — BTC-ETH-USDT 삼각형, ~6.7% 수익
_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000, "ask": 50000, "last": 50000},
    "ETH/BTC": {"bid": 0.06, "ask": 0.06, "last": 0.06},
    "ETH/USDT": {"bid": 3200, "ask": 3200, "last": 3200},
}

# 공정 가격 — spread 적용, 차익 없음
_FAIR_TICKERS = {
    "BTC/USDT": {"bid": 49999, "ask": 50001, "last": 50000},
    "ETH/BTC": {"bid": 0.05999, "ask": 0.06001, "last": 0.06},
    "ETH/USDT": {"bid": 2999, "ask": 3001, "last": 3000},
}


class _FakeAdapter(ExchangeInterface):
    async def subscribe_ticker(self, trading_pairs, callback) -> None:
        pass

    async def place_order(self, order: Order) -> OrderResult:
        raise NotImplementedError

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        raise NotImplementedError

    async def get_balance(self) -> Balance:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        pass


class _FakeStateMachine:
    def __init__(self) -> None:
        self.started: list[ArbSignal] = []

    async def start(self, signal: ArbSignal) -> None:
        self.started.append(signal)


def _make_runner(
    sm: _FakeStateMachine,
    min_profit: Decimal = Decimal("0.002"),
) -> tuple[LiveRunner, asyncio.Queue]:
    tick_queue: asyncio.Queue = asyncio.Queue()
    bus = EventBus()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, bus=bus, tick_queue=tick_queue)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0.01"),
        min_profit=min_profit,
    )
    # USDT-notional limits sized generously so prices fed from _ARB_TICKERS pass risk.
    engine = ExecutionEngine(
        risk_manager=RiskManager(max_order_size=Decimal("1e9"), max_exposure=Decimal("1e9")),
        state_machine=sm,
    )
    runner = LiveRunner(
        exchange=_FakeAdapter(),
        feed=feed,
        strategy=strategy,
        engine=engine,
    )
    return runner, tick_queue


async def test_arb_tickers_signal_reaches_state_machine():
    sm = _FakeStateMachine()
    runner, _ = _make_runner(sm)
    await runner.on_tickers(_ARB_TICKERS)
    assert len(sm.started) == 1


async def test_fair_tickers_no_signal():
    sm = _FakeStateMachine()
    runner, _ = _make_runner(sm)
    await runner.on_tickers(_FAIR_TICKERS)
    assert len(sm.started) == 0


async def test_ticks_enqueued_to_tick_queue():
    sm = _FakeStateMachine()
    runner, tick_queue = _make_runner(sm)
    await runner.on_tickers(_FAIR_TICKERS)
    assert tick_queue.qsize() == 3  # 3개 심볼 → 3개 tick


async def test_kill_switch_blocks_signal():
    sm = _FakeStateMachine()
    runner, _ = _make_runner(sm)
    runner._engine._risk.set_kill_switch(True)
    await runner.on_tickers(_ARB_TICKERS)
    assert len(sm.started) == 0


async def test_consecutive_arb_calls_each_produce_signal():
    sm = _FakeStateMachine()
    runner, _ = _make_runner(sm)
    await runner.on_tickers(_ARB_TICKERS)
    await runner.on_tickers(_ARB_TICKERS)
    assert len(sm.started) == 2


async def test_partial_then_full_prices_trigger_signal():
    sm = _FakeStateMachine()
    runner, _ = _make_runner(sm)
    # 첫 번째 호출: BTC/USDT, ETH/USDT만 (삼각형 미완성)
    await runner.on_tickers(
        {
            "BTC/USDT": {"bid": 50000, "ask": 50000, "last": 50000},
            "ETH/USDT": {"bid": 3200, "ask": 3200, "last": 3200},
        }
    )
    assert len(sm.started) == 0

    # 두 번째 호출: ETH/BTC 추가 → 캐시와 합쳐 삼각형 완성
    await runner.on_tickers(
        {
            "ETH/BTC": {"bid": 0.06, "ask": 0.06, "last": 0.06},
        }
    )
    assert len(sm.started) == 1
