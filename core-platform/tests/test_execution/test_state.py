import asyncio
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side
from atlas.execution.state import ArbitrageStateMachine, State

_PAIR = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_SIGNAL = ArbSignal(
    exchange=Exchange.BINANCE,
    leg1_pair=_PAIR,
    leg1_side=Side.BUY,
    leg1_quantity=Decimal("0.01"),
    leg2_pair=_PAIR,
    leg2_side=Side.BUY,
    leg2_quantity=Decimal("0.01"),
    leg3_pair=_PAIR,
    leg3_side=Side.SELL,
    leg3_quantity=Decimal("0.01"),
    expected_profit=Decimal("5"),
)


class _FakeExchange:
    """Records placed orders. hang_on: set of call-indices (0-based) where place_order will hang."""

    def __init__(self, *, hang_on: set[int] | None = None) -> None:
        self.placed: list[Order] = []
        self._hang_on = hang_on or set()

    async def place_order(self, order: Order) -> OrderResult:
        call_idx = len(self.placed)
        self.placed.append(order)
        if call_idx in self._hang_on:
            await asyncio.sleep(100)  # triggers timeout in caller
        return OrderResult(id=order.id, status=OrderStatus.FILLED, filled=float(order.quantity))


def _sm(exchange: _FakeExchange) -> ArbitrageStateMachine:
    return ArbitrageStateMachine(
        exchange=exchange, leg1_timeout=0.01, leg2_timeout=0.01, leg3_timeout=0.01
    )


async def test_happy_path_places_three_orders_and_returns_idle():
    exchange = _FakeExchange()
    sm = _sm(exchange)

    await sm.start(_SIGNAL)

    assert sm.state == State.IDLE
    assert len(exchange.placed) == 3
    assert exchange.placed[0].side == Side.BUY  # leg1
    assert exchange.placed[1].side == Side.BUY  # leg2
    assert exchange.placed[2].side == Side.SELL  # leg3


async def test_leg1_timeout_returns_idle():
    # call #0 appended then hangs → timeout → 1 in placed (the timed-out LEG1 order)
    exchange = _FakeExchange(hang_on={0})
    sm = _sm(exchange)

    await sm.start(_SIGNAL)

    assert sm.state == State.IDLE
    assert len(exchange.placed) == 1


async def test_leg2_timeout_unwinds_leg1():
    # call #0: LEG1 success
    # call #1: LEG2 appended then hangs → timeout
    # call #2: unwind LEG1 (BUY → SELL)
    exchange = _FakeExchange(hang_on={1})
    sm = _sm(exchange)

    await sm.start(_SIGNAL)

    assert sm.state == State.IDLE
    assert len(exchange.placed) == 3
    assert exchange.placed[2].side == Side.SELL  # unwind of leg1 (BUY → SELL)


async def test_leg3_timeout_unwinds_leg2_then_leg1():
    # call #0: LEG1 success
    # call #1: LEG2 success
    # call #2: LEG3 appended then hangs → timeout
    # call #3: unwind LEG2 (BUY → SELL)
    # call #4: unwind LEG1 (BUY → SELL)
    exchange = _FakeExchange(hang_on={2})
    sm = _sm(exchange)

    await sm.start(_SIGNAL)

    assert sm.state == State.IDLE
    assert len(exchange.placed) == 5
    assert exchange.placed[3].side == Side.SELL  # unwind leg2
    assert exchange.placed[4].side == Side.SELL  # unwind leg1


async def test_start_while_not_idle_is_ignored():
    exchange = _FakeExchange()
    sm = _sm(exchange)
    sm.state = State.LEG1_PENDING

    await sm.start(_SIGNAL)

    assert len(exchange.placed) == 0
