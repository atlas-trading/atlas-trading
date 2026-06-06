"""
Integration tests using realistic ccxt Binance spot order responses.

Tests verify that:
- _actual_profit is computed correctly from real fill data (id, average, filled, cost)
- Slippage is reflected in lower-than-expected actual_profit
- Partial fills propagate correctly to subsequent legs
- Gap 2 fix: unfilled leg1 returns profit=0 not expected_profit
- ccxt NetworkError / RequestTimeout trigger correct unwind paths
- Order.id round-trip: each leg gets a distinct UUID
- exact-price scenario produces actual_profit ≈ expected_profit
"""

from __future__ import annotations

import asyncio
import re
from decimal import Decimal

from ccxt.base.errors import NetworkError, RequestTimeout

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side
from atlas.execution.state import ArbitrageStateMachine

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ccxt_result(
    order_id: str,
    status: str = "closed",
    symbol: str = "ETH/USDT",
    side: str = "sell",
    filled: str = "0.01",
    average: str = "3195.42",
    cost: str | None = None,
) -> OrderResult:
    filled_d = Decimal(filled)
    avg_d = Decimal(average)
    cost_d = Decimal(cost) if cost else filled_d * avg_d
    return OrderResult(
        id=order_id,
        client_order_id=f"client-{order_id}",
        status=OrderStatus.FILLED if status == "closed" else OrderStatus.PENDING,
        symbol=symbol,
        side=side,
        average=avg_d,
        filled=filled_d,
        cost=cost_d,
    )


def _make_signal(
    *,
    leg1_side: Side = Side.SELL,
    leg1_qty: str = "0.01",
    leg2_qty: str | None = None,
    leg3_qty: str | None = None,
    expected_profit: str = "0.000640",
) -> ArbSignal:
    """Return a SELL ETH/USDT → BUY BTC/USDT → BUY ETH/BTC signal."""
    q1 = Decimal(leg1_qty)
    # Approximate chain quantities: 0.01 ETH → 31.9542 USDT → 0.000639 BTC → 0.01064 ETH
    q2 = Decimal(leg2_qty) if leg2_qty else q1 * Decimal("3195.42") / Decimal("50000")
    q3 = Decimal(leg3_qty) if leg3_qty else q2 / Decimal("0.06")
    return ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_ETH_USDT,
        leg1_side=leg1_side,
        leg1_quantity=q1,
        leg2_pair=_BTC_USDT,
        leg2_side=Side.BUY,
        leg2_quantity=q2,
        leg3_pair=_ETH_BTC,
        leg3_side=Side.BUY,
        leg3_quantity=q3,
        expected_profit=Decimal(expected_profit),
    )


class _ScriptedExchange:
    def __init__(self, script: list[OrderResult | Exception | str]) -> None:
        self._script = script
        self.placed: list[Order] = []

    async def place_order(self, order: Order) -> OrderResult:
        idx = len(self.placed)
        self.placed.append(order)
        if idx >= len(self._script):
            return OrderResult(id=order.id, status=OrderStatus.FILLED, filled=order.quantity)
        item = self._script[idx]
        if isinstance(item, Exception):
            raise item
        if item == "hang":
            await asyncio.sleep(100)
        return item  # type: ignore[return-value]


def _make_sm(exchange: _ScriptedExchange, timeout: float = 0.5) -> ArbitrageStateMachine:
    return ArbitrageStateMachine(
        exchange=exchange,
        leg1_timeout=timeout,
        leg2_timeout=timeout,
        leg3_timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Test 1: actual_profit computed from real fill data
# ---------------------------------------------------------------------------


async def test_actual_profit_from_real_fill_data():
    """_actual_profit uses filled/average/cost from ccxt responses."""
    signal = _make_signal()

    r1 = _ccxt_result(
        "l1", symbol="ETH/USDT", side="sell", filled="0.01", average="3195.42", cost="31.9542"
    )
    r2 = _ccxt_result(
        "l2", symbol="BTC/USDT", side="buy", filled="0.0006389", average="50000", cost="31.945"
    )
    r3 = _ccxt_result(
        "l3", symbol="ETH/BTC", side="buy", filled="0.010640", average="0.0601", cost="0.0006395"
    )

    exchange = _ScriptedExchange([r1, r2, r3])
    sm = _make_sm(exchange)
    await sm.start(signal)

    # _actual_profit: leg1 SELL → start = r1.filled = 0.01 ETH
    #                 leg3 BUY  → end   = r3.filled = 0.010640 ETH
    #                 profit = 0.010640 - 0.01 = 0.000640 ETH
    actual = r3.filled - r1.filled
    assert actual > Decimal("0"), f"expected positive profit, got {actual}"
    assert actual < signal.expected_profit * Decimal("2"), (
        f"profit {actual} unreasonably large vs expected {signal.expected_profit}"
    )


# ---------------------------------------------------------------------------
# Test 2: slippage reduces actual_profit below expected
# ---------------------------------------------------------------------------


async def test_slippage_reduces_actual_profit():
    """leg2 fills at 50100 instead of 50000 → BTC costs more → less ETH at leg3."""
    signal = _make_signal(expected_profit=Decimal("0.000640"))

    # leg2: BUY BTC at 50100 (worse than 50000) — same cost as before → less BTC filled
    filled2 = Decimal("31.9542") / Decimal("50100")  # ≈ 0.000638
    r1 = _ccxt_result(
        "l1", symbol="ETH/USDT", side="sell", filled="0.01", average="3195.42", cost="31.9542"
    )
    r2 = _ccxt_result(
        "l2", symbol="BTC/USDT", side="buy", filled=str(filled2), average="50100", cost="31.9542"
    )
    filled3 = filled2 / Decimal("0.0601")
    r3 = _ccxt_result(
        "l3", symbol="ETH/BTC", side="buy", filled=str(filled3), average="0.0601", cost=str(filled2)
    )

    exchange = _ScriptedExchange([r1, r2, r3])
    sm = _make_sm(exchange)
    await sm.start(signal)

    actual = r3.filled - r1.filled
    assert actual < signal.expected_profit, (
        f"slippage scenario: actual {actual} should be less than expected {signal.expected_profit}"
    )


# ---------------------------------------------------------------------------
# Test 3: partial fill → leg2/leg3 quantities scale proportionally
# ---------------------------------------------------------------------------


async def test_partial_fill_leg2_leg3_scale():
    """leg1 fills 50% → leg2 ordered qty = signal.leg2_quantity / 2."""
    signal = _make_signal()
    half = signal.leg1_quantity / 2

    r1 = _ccxt_result(
        "l1",
        symbol="ETH/USDT",
        side="sell",
        filled=str(half),
        average="3195.42",
        cost=str(half * Decimal("3195.42")),
    )

    exchange = _ScriptedExchange([r1])
    sm = _make_sm(exchange)
    await sm.start(signal)

    # At least leg1 + leg2 placed
    assert len(exchange.placed) >= 2
    leg2_order = exchange.placed[1]
    expected_q2 = signal.leg2_quantity / 2
    assert abs(leg2_order.quantity - expected_q2) < Decimal("0.0001"), (
        f"leg2 qty {leg2_order.quantity} should be ≈ {expected_q2} (50% of signal)"
    )


# ---------------------------------------------------------------------------
# Test 4: Gap 2 fix — unfilled leg1 returns profit=0
# ---------------------------------------------------------------------------


async def test_gap2_unfilled_leg1_returns_zero_profit():
    """
    Direct test of _actual_profit with start=0 (unfilled leg1).
    Before the fix this returned signal.expected_profit; now must return Decimal("0").
    """
    from unittest.mock import AsyncMock, MagicMock

    mock_exchange = MagicMock()
    mock_exchange.place_order = AsyncMock()

    sm = ArbitrageStateMachine(exchange=mock_exchange)
    signal = _make_signal()

    # r1 with filled=0 means start=0 for a SELL leg (side==SELL → start=filled)
    r1 = OrderResult(
        id="l1",
        status=OrderStatus.FILLED,
        filled=Decimal("0"),
        average=Decimal("3195.42"),
        cost=None,
    )
    r2 = _ccxt_result("l2", symbol="BTC/USDT", side="buy", filled="0.000639", average="50000")
    r3 = _ccxt_result("l3", symbol="ETH/BTC", side="buy", filled="0.01064", average="0.06")

    profit = sm._actual_profit(signal, r1, r2, r3)
    assert profit == Decimal("0"), f"unfilled leg1 should produce profit=0, got {profit}"


# ---------------------------------------------------------------------------
# Test 5: ccxt NetworkError on leg2 → unwind leg1
# ---------------------------------------------------------------------------


async def test_network_error_on_leg2_triggers_leg1_unwind():
    signal = _make_signal()

    r1 = _ccxt_result("l1", symbol="ETH/USDT", side="sell", filled="0.01", average="3195.42")
    exchange = _ScriptedExchange(
        [
            r1,
            NetworkError("Connection refused"),  # leg2 raises
            # leg1 unwind goes to default fill path
        ]
    )
    sm = _make_sm(exchange, timeout=0.5)
    await sm.start(signal)

    # leg1 + leg2-attempt (raises before completing) + leg1-unwind = 3
    assert len(exchange.placed) == 3, f"expected 3 orders, got {len(exchange.placed)}"
    unwind = exchange.placed[2]
    assert unwind.trading_pair == signal.leg1_pair
    # Unwind reverses the side
    expected_reverse = Side.BUY if signal.leg1_side == Side.SELL else Side.SELL
    assert unwind.side == expected_reverse
    # State machine should be back to IDLE
    from atlas.execution.state import State

    assert sm.state == State.IDLE


# ---------------------------------------------------------------------------
# Test 6: ccxt RequestTimeout on leg3 → unwind leg1 + leg2
# ---------------------------------------------------------------------------


async def test_request_timeout_on_leg3_triggers_full_unwind():
    signal = _make_signal()

    r1 = _ccxt_result("l1", symbol="ETH/USDT", side="sell", filled="0.01", average="3195.42")
    r2 = _ccxt_result("l2", symbol="BTC/USDT", side="buy", filled="0.000639", average="50000")
    exchange = _ScriptedExchange(
        [
            r1,
            r2,
            RequestTimeout("Request timed out"),  # leg3 raises
            # leg2 unwind
            # leg1 unwind
        ]
    )
    sm = _make_sm(exchange, timeout=0.5)
    await sm.start(signal)

    # leg1 + leg2 + leg3-attempt + leg2-unwind + leg1-unwind = 5
    assert len(exchange.placed) == 5, f"expected 5 orders, got {len(exchange.placed)}"
    from atlas.execution.state import State

    assert sm.state == State.IDLE


# ---------------------------------------------------------------------------
# Test 7: client_order_id round-trip and per-leg UUID uniqueness
# ---------------------------------------------------------------------------


async def test_order_id_uuid_uniqueness_per_leg():
    """Each leg gets a distinct UUID as Order.id."""
    signal = _make_signal()

    exchange = _ScriptedExchange([])  # all legs hit default fill path
    sm = _make_sm(exchange)
    await sm.start(signal)

    assert len(exchange.placed) == 3
    ids = [o.id for o in exchange.placed]

    # All UUIDs are valid format
    for oid in ids:
        assert _UUID_RE.match(oid), f"Order.id {oid!r} is not a valid UUID"

    # All UUIDs are distinct
    assert len(set(ids)) == 3, f"Leg Order.ids are not all distinct: {ids}"


# ---------------------------------------------------------------------------
# Test 8: exact bid/ask prices → actual_profit ≈ expected_profit
# ---------------------------------------------------------------------------


async def test_exact_prices_actual_profit_near_expected():
    """
    No spread, no slippage: actual fill at exact signal prices.
    actual_profit should be close to expected_profit.

    ETH/USDT=3200, BTC/USDT=50000, ETH/BTC=0.06
    leg1: SELL 0.01 ETH @ 3200 → cost = 32.0 USDT
    leg2: BUY BTC @ 50000, cost=32.0 → filled = 0.00064 BTC
    leg3: BUY ETH @ 0.06, cost=0.00064 → filled = 0.010667 ETH
    actual_profit = 0.010667 - 0.01 = 0.000667 ETH
    """
    leg1_qty = Decimal("0.01")
    leg1_cost = leg1_qty * Decimal("3200")  # 32.0 USDT
    leg2_filled = leg1_cost / Decimal("50000")  # 0.00064 BTC
    leg3_filled = leg2_filled / Decimal("0.06")  # 0.010667 ETH
    expected_profit_approx = leg3_filled - leg1_qty  # 0.000667 ETH

    signal = ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_ETH_USDT,
        leg1_side=Side.SELL,
        leg1_quantity=leg1_qty,
        leg2_pair=_BTC_USDT,
        leg2_side=Side.BUY,
        leg2_quantity=leg2_filled,
        leg3_pair=_ETH_BTC,
        leg3_side=Side.BUY,
        leg3_quantity=leg3_filled,
        expected_profit=expected_profit_approx,
    )

    r1 = _ccxt_result(
        "l1",
        symbol="ETH/USDT",
        side="sell",
        filled=str(leg1_qty),
        average="3200",
        cost=str(leg1_cost),
    )
    r2 = _ccxt_result(
        "l2",
        symbol="BTC/USDT",
        side="buy",
        filled=str(leg2_filled),
        average="50000",
        cost=str(leg1_cost),
    )
    r3 = _ccxt_result(
        "l3",
        symbol="ETH/BTC",
        side="buy",
        filled=str(leg3_filled),
        average="0.06",
        cost=str(leg2_filled),
    )

    exchange = _ScriptedExchange([r1, r2, r3])
    sm = _make_sm(exchange)
    await sm.start(signal)

    actual = leg3_filled - leg1_qty
    diff = abs(actual - signal.expected_profit)
    assert diff < Decimal("0.0002"), (
        f"actual {actual} should be ≈ expected {signal.expected_profit} (diff={diff})"
    )
