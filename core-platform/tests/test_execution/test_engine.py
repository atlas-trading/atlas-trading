from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.engine import ExecutionEngine
from atlas.execution.side import Side
from atlas.risk.manager import RiskManager

_PAIR = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)


class _FakeStateMachine:
    def __init__(self) -> None:
        self.started: list[ArbSignal] = []

    async def start(self, signal: ArbSignal) -> None:
        self.started.append(signal)


def _make_signal() -> ArbSignal:
    qty = Decimal("0.01")
    return ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_PAIR,
        leg1_side=Side.BUY,
        leg1_quantity=qty,
        leg2_pair=_PAIR,
        leg2_side=Side.BUY,
        leg2_quantity=qty,
        leg3_pair=_PAIR,
        leg3_side=Side.SELL,
        leg3_quantity=qty,
        expected_profit=Decimal("5"),
    )


async def test_approved_signal_starts_state_machine():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    sm = _FakeStateMachine()
    engine = ExecutionEngine(risk_manager=rm, state_machine=sm)

    await engine.on_signal(_make_signal())

    assert len(sm.started) == 1


async def test_rejected_signal_skips_state_machine():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    rm.set_kill_switch(True)
    sm = _FakeStateMachine()
    engine = ExecutionEngine(risk_manager=rm, state_machine=sm)

    await engine.on_signal(_make_signal())

    assert len(sm.started) == 0


async def test_multiple_signals_only_approved_forwarded():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    sm = _FakeStateMachine()
    engine = ExecutionEngine(risk_manager=rm, state_machine=sm)

    await engine.on_signal(_make_signal())
    rm.set_kill_switch(True)
    await engine.on_signal(_make_signal())
    await engine.on_signal(_make_signal())

    assert len(sm.started) == 1
