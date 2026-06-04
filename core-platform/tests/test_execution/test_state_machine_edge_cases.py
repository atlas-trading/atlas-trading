"""
Edge-case tests for ArbitrageStateMachine.

These probe known weak spots:
  * partial fills — leg2 plans for X but only Y < X arrives; unwind uses
    `result.filled`, but subsequent legs still use the SIGNAL'S planned qty
    leading to a position mismatch.
  * concurrent signals during in-flight execution
  * unwind failure paths
  * cancellation propagation
  * absence of `filled` field in OrderResult (None) on unwind
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

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

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)


def _signal(
    q1: Decimal = Decimal("0.01"),
    q2: Decimal = Decimal("0.1667"),
    q3: Decimal = Decimal("0.1667"),
) -> ArbSignal:
    return ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_BTC_USDT,
        leg1_side=Side.BUY,
        leg1_quantity=q1,
        leg2_pair=_ETH_BTC,
        leg2_side=Side.BUY,
        leg2_quantity=q2,
        leg3_pair=_ETH_USDT,
        leg3_side=Side.SELL,
        leg3_quantity=q3,
        expected_profit=Decimal("0.5"),
    )


class _ScriptedExchange:
    """
    Returns pre-scripted OrderResult objects (or raises / hangs) per call index.
    """

    def __init__(self, script: list[OrderResult | Exception | str]) -> None:
        self._script = script
        self.placed: list[Order] = []

    async def place_order(self, order: Order) -> OrderResult:
        idx = len(self.placed)
        self.placed.append(order)
        if idx >= len(self._script):
            # Default: fully filled
            return OrderResult(id=order.id, status=OrderStatus.FILLED, filled=order.quantity)
        item = self._script[idx]
        if isinstance(item, Exception):
            raise item
        if item == "hang":
            await asyncio.sleep(100)
        return item  # type: ignore[return-value]


def _sm(exchange: _ScriptedExchange, timeout: float = 0.01) -> ArbitrageStateMachine:
    return ArbitrageStateMachine(
        exchange=exchange,
        leg1_timeout=timeout,
        leg2_timeout=timeout,
        leg3_timeout=timeout,
    )


# --------------------------------------------------------------------------- #
# 1. PARTIAL FILL EDGE CASES
# --------------------------------------------------------------------------- #


async def test_leg1_partial_fill_leg2_uses_signal_qty_not_actual_filled():
    """
    BUG: when leg1 partially fills (filled=0.005 vs requested 0.01), the state
    machine still places leg2 for `signal.leg2_quantity` — which was sized for
    the FULL leg1 fill. Result: leg2 over-trades by 2x.

    A correct implementation would either:
      (a) re-compute leg2/leg3 quantities from leg1.filled, or
      (b) cancel leg1 and unwind only the filled portion.
    """
    sig = _signal()
    # leg1 returns half-fill; leg2, leg3 default full fill
    half = sig.leg1_quantity / 2
    leg1_result = OrderResult(id="x1", status=OrderStatus.FILLED, filled=half)
    exchange = _ScriptedExchange([leg1_result])
    sm = _sm(exchange)

    await sm.start(sig)

    # If logic is correct, leg2 should be sized off the *filled* leg1 amount.
    # Current code passes signal.leg2_quantity unchanged. This assertion FAILS
    # under the buggy current behaviour.
    leg2_order = exchange.placed[1]
    assert leg2_order.quantity < sig.leg2_quantity, (
        f"leg2 placed at full signal qty {sig.leg2_quantity} despite leg1 "
        f"partial fill ({half} of {sig.leg1_quantity}). "
        "State machine ignores actual fill quantity — position mismatch."
    )


async def test_leg2_partial_fill_leg3_oversells():
    """
    Similar to above, but at leg2. leg3 will sell more ETH than was actually
    bought, leading to a short position.
    """
    sig = _signal()
    leg1_full = OrderResult(id="o1", status=OrderStatus.FILLED, filled=sig.leg1_quantity)
    leg2_half = OrderResult(id="o2", status=OrderStatus.FILLED, filled=sig.leg2_quantity / 2)
    exchange = _ScriptedExchange([leg1_full, leg2_half])
    sm = _sm(exchange)

    await sm.start(sig)

    leg3_order = exchange.placed[2]
    assert leg3_order.quantity <= sig.leg2_quantity / 2, (
        f"leg3 placed at signal qty {leg3_order.quantity} ignoring leg2 "
        f"partial fill of {sig.leg2_quantity / 2}. Will oversell."
    )


async def test_unwind_uses_actual_filled_quantity():
    """
    On unwind, the state machine reverses `result.filled` — this part is
    correct. Verify that a partial fill on leg1 followed by a leg2 timeout
    results in an unwind sized to the actual fill (not the signal qty).
    """
    sig = _signal()
    half = sig.leg1_quantity / 2
    leg1_partial = OrderResult(id="o1", status=OrderStatus.FILLED, filled=half)
    exchange = _ScriptedExchange([leg1_partial, "hang"])
    sm = _sm(exchange)

    await sm.start(sig)

    # placed[0] = leg1 (partial), placed[1] = leg2 (hang→timeout), placed[2] = unwind
    assert len(exchange.placed) == 3
    unwind = exchange.placed[2]
    assert unwind.side == Side.SELL  # reverse of BUY leg1
    assert unwind.quantity == half  # ← reverses actual fill, not signal qty


async def test_unwind_skipped_when_filled_is_none():
    """
    OrderResult.filled may be None (some exchanges omit it on aborted orders).
    _unwind has `filled = result.filled if result.filled else Decimal("0")`
    so a None or 0 filled → no unwind order. Test confirms no extra order.
    """
    sig = _signal()
    leg1_unknown = OrderResult(
        id="o1",
        status=OrderStatus.FILLED,
        filled=None,  # ← no fill amount reported
    )
    exchange = _ScriptedExchange([leg1_unknown, "hang"])
    sm = _sm(exchange)

    await sm.start(sig)

    # leg1 (None filled), leg2 (timeout), no unwind because filled is None
    assert len(exchange.placed) == 2
    # filled=None should NOT silently treat as a full-fill needing reversal.


# --------------------------------------------------------------------------- #
# 2. CONCURRENCY / STATE GUARDING
# --------------------------------------------------------------------------- #


async def test_concurrent_start_during_leg2_pending_is_dropped():
    """A second start() while LEG2_PENDING must be a no-op."""
    sig = _signal()
    # leg2 hangs forever; we'll fire a concurrent start() against the same SM.
    exchange = _ScriptedExchange(
        [
            OrderResult(id="o1", status=OrderStatus.FILLED, filled=sig.leg1_quantity),
            "hang",
        ]
    )
    sm = _sm(exchange, timeout=0.1)

    task = asyncio.create_task(sm.start(sig))
    # Wait long enough for LEG1 to fill and LEG2 to begin hanging.
    await asyncio.sleep(0.02)
    # Second start during in-flight should be ignored.
    placed_before = len(exchange.placed)
    await sm.start(sig)
    placed_after_2nd_start = len(exchange.placed)
    assert placed_after_2nd_start == placed_before, (
        "Concurrent start() during pending leg added orders — state guard broken."
    )
    await task  # let leg2 timeout and unwind complete


async def test_two_back_to_back_starts_each_complete_independently():
    """First start completes (state→IDLE), second start should execute fresh."""
    sig = _signal()
    exchange = _ScriptedExchange([])  # all default-fill
    sm = _sm(exchange, timeout=1.0)

    await sm.start(sig)
    assert sm.state == State.IDLE
    placed_after_1 = len(exchange.placed)

    await sm.start(sig)
    assert sm.state == State.IDLE
    assert len(exchange.placed) == placed_after_1 + 3


# --------------------------------------------------------------------------- #
# 3. UNWIND FAILURES
# --------------------------------------------------------------------------- #


async def test_unwind_failure_after_leg3_timeout_still_returns_to_idle():
    """
    leg1 fills, leg2 fills, leg3 times out, unwind of leg2 raises.
    `finally` must restore IDLE so the loop can accept new signals.
    """
    sig = _signal()
    exchange = _ScriptedExchange(
        [
            OrderResult(id="o1", status=OrderStatus.FILLED, filled=sig.leg1_quantity),
            OrderResult(id="o2", status=OrderStatus.FILLED, filled=sig.leg2_quantity),
            "hang",  # leg3 timeout
            RuntimeError("unwind leg2 failed"),
        ]
    )
    sm = _sm(exchange)

    await sm.start(sig)

    assert sm.state == State.IDLE, (
        "State machine stuck off-IDLE after unwind failure — will reject "
        "future signals indefinitely."
    )


async def test_leg2_timeout_unwind_leg1_quantity_matches_leg1_filled():
    """Sanity: unwind of leg1 reverses exactly leg1's filled quantity."""
    sig = _signal()
    leg1_filled = sig.leg1_quantity * Decimal("0.7")
    exchange = _ScriptedExchange(
        [
            OrderResult(id="o1", status=OrderStatus.FILLED, filled=leg1_filled),
            "hang",
        ]
    )
    sm = _sm(exchange)

    await sm.start(sig)

    unwind = exchange.placed[2]
    assert unwind.quantity == leg1_filled
    assert unwind.trading_pair == sig.leg1_pair
    assert unwind.side == Side.SELL  # reversal of BUY


# --------------------------------------------------------------------------- #
# 4. CANCELLATION SEMANTICS
# --------------------------------------------------------------------------- #


async def test_cancelled_error_propagates_no_unwind():
    """CancelledError must propagate without triggering unwind (asyncio shutdown)."""
    sig = _signal()
    exchange = _ScriptedExchange(
        [
            OrderResult(id="o1", status=OrderStatus.FILLED, filled=sig.leg1_quantity),
            "hang",  # leg2 will hang
        ]
    )
    sm = _sm(exchange, timeout=10.0)  # long timeout so we cancel manually

    task = asyncio.create_task(sm.start(sig))
    await asyncio.sleep(0.02)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    # State machine swallowed cancellation — confirm state is IDLE (the finally
    # block resets state regardless).
    assert sm.state == State.IDLE
    # Critically, no unwind order was placed (leg1 fill, leg2 hang, cancel
    # before timeout → 2 placed, no unwind).
    assert len(exchange.placed) == 2


# --------------------------------------------------------------------------- #
# 5. SAME-SIDE LEG SIGNALS (degenerate cycles)
# --------------------------------------------------------------------------- #


async def test_signal_with_all_sells_still_executes():
    """
    A degenerate signal where all three legs are SELL (no economic sense, but
    not validated by the state machine). The machine should still execute or
    reject — it must not crash.
    """
    bad_sig = ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_BTC_USDT,
        leg1_side=Side.SELL,
        leg1_quantity=Decimal("0.01"),
        leg2_pair=_ETH_BTC,
        leg2_side=Side.SELL,
        leg2_quantity=Decimal("0.01"),
        leg3_pair=_ETH_USDT,
        leg3_side=Side.SELL,
        leg3_quantity=Decimal("0.01"),
        expected_profit=Decimal("0"),
    )
    exchange = _ScriptedExchange([])
    sm = _sm(exchange, timeout=1.0)
    await sm.start(bad_sig)
    assert sm.state == State.IDLE
    # State machine has no signal-validity check; it places all 3 SELLs.
    assert len(exchange.placed) == 3
    assert all(o.side == Side.SELL for o in exchange.placed)
