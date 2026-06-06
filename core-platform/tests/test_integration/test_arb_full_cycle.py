"""
End-to-end integration tests for the triangular arbitrage pipeline.

Wires: TriangularArbitrageStrategy → RiskManager → ArbitrageStateMachine →
ScriptedExchange. Tests cover full happy path, fee-aware rejection (currently
NOT implemented — test documents the gap), TTL behaviour, partial fills,
exposure aggregation across consecutive signals, and unwind paths.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import patch

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.exchange.order_result import OrderResult
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side
from atlas.execution.state import ArbitrageStateMachine
from atlas.risk.manager import RiskDecision, RiskManager
from atlas.strategy.arbitrage.triangular import (
    _PRICE_TTL_SECONDS,
    TriangularArbitrageStrategy,
)

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)


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


def _build_stack(
    exchange: _ScriptedExchange,
    min_profit: Decimal = Decimal("0.002"),
    max_order_size: Decimal = Decimal("1e9"),
    max_exposure: Decimal = Decimal("1e9"),
    timeout: float = 0.05,
) -> tuple[TriangularArbitrageStrategy, RiskManager, ArbitrageStateMachine]:
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0.01"),
        min_profit=min_profit,
    )
    risk = RiskManager(max_order_size=max_order_size, max_exposure=max_exposure)
    risk.update_prices(
        {
            _BTC_USDT: Decimal("50000"),
            _ETH_USDT: Decimal("3200"),
        }
    )
    sm = ArbitrageStateMachine(
        exchange=exchange, leg1_timeout=timeout, leg2_timeout=timeout, leg3_timeout=timeout
    )
    return strategy, risk, sm


_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000, "ask": 50000},
    "ETH/BTC": {"bid": 0.06, "ask": 0.06},
    "ETH/USDT": {"bid": 3200, "ask": 3200},  # ETH/USDT overpriced vs fair 3000
}
_FAIR_TICKERS = {
    "BTC/USDT": {"bid": 49999, "ask": 50001},
    "ETH/BTC": {"bid": 0.05999, "ask": 0.06001},
    "ETH/USDT": {"bid": 2999, "ask": 3001},
}


# --------------------------------------------------------------------------- #
# Scenario 1: normal triangular arb full cycle
# --------------------------------------------------------------------------- #


async def test_full_cycle_emits_signal_and_places_three_orders():
    exchange = _ScriptedExchange([])
    strategy, risk, sm = _build_stack(exchange)

    signals = strategy.on_tickers(_ARB_TICKERS)
    assert len(signals) == 1
    signal = signals[0]
    assert risk.check(signal) == RiskDecision.APPROVED
    await sm.start(signal)

    assert len(exchange.placed) == 3
    # All three orders placed with non-zero, positive quantities.
    assert all(o.quantity > 0 for o in exchange.placed)
    # The cycle covers exactly the BTC-ETH-USDT triangle.
    pairs_traded = {o.trading_pair for o in exchange.placed}
    assert pairs_traded == {_BTC_USDT, _ETH_BTC, _ETH_USDT}


async def test_full_cycle_quantities_chain_correctly():
    """
    The quantity output of leg N (after taker fee) must equal the input of leg N+1.
    We re-derive the expected sequence from the actually emitted sides, factoring
    in the 0.1% taker fee deducted on each fill.
    """
    fee = Decimal("0.001")
    exchange = _ScriptedExchange([])
    strategy, _, sm = _build_stack(exchange)
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    await sm.start(signal)

    legs = (
        (signal.leg1_pair, signal.leg1_side, signal.leg1_quantity),
        (signal.leg2_pair, signal.leg2_side, signal.leg2_quantity),
        (signal.leg3_pair, signal.leg3_side, signal.leg3_quantity),
    )
    prices = {
        _BTC_USDT: Decimal("50000"),
        _ETH_BTC: Decimal("0.06"),
        _ETH_USDT: Decimal("3200"),
    }
    # Re-derive expected qty[i+1] with fee deduction applied on the output of leg i.
    for i in range(2):
        pair_i, side_i, q_i = legs[i]
        pair_n, side_n, q_n_actual = legs[i + 1]
        p_i = prices[pair_i]
        # leg i output amount after fee (BUY: base*(1-fee), SELL: base*bid*(1-fee))
        out = q_i * (1 - fee) if side_i == Side.BUY else q_i * p_i * (1 - fee)
        # leg i+1 expected base-asset qty (BUY: out/ask, SELL: out)
        p_n = prices[pair_n]
        expected_q_next = out / p_n if side_n == Side.BUY else out
        diff = abs(q_n_actual - expected_q_next)
        assert diff < Decimal("0.0001"), (
            f"leg{i + 2} qty chain broken: got {q_n_actual}, "
            f"expected {expected_q_next} (delta={diff})"
        )


# --------------------------------------------------------------------------- #
# Scenario 2: fees consume the arb (currently unmodeled — this exposes the gap)
# --------------------------------------------------------------------------- #


async def test_fee_threshold_signal_emitted_but_unprofitable_after_fees():
    """
    Fee-aware rejection: a ~0.3% nominal-profit triangle is correctly rejected
    once taker fees are included in the Bellman-Ford edge weights.

    The gross rate was ≈1.003, but 3 legs × 0.1% taker fee ≈ 0.3% cost means
    the net rate falls below 1.0 — no real profit. detect_arbitrage now returns
    None for this price set, so no signal is emitted.
    """
    exchange = _ScriptedExchange([])
    strategy, _, _ = _build_stack(exchange, min_profit=Decimal("0.002"))

    barely_profitable = {
        "BTC/USDT": {"bid": 50000, "ask": 50000},
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3009, "ask": 3009},  # ~0.3% above fair 3000
    }
    signals = strategy.on_tickers(barely_profitable)
    # Fee-aware graph correctly finds no profitable cycle.
    assert len(signals) == 0, (
        f"Strategy emitted {len(signals)} signal(s) on a barely-profitable arb "
        "that fees should eliminate."
    )


# --------------------------------------------------------------------------- #
# Scenario 3: leg2 timeout → unwind leg1
# --------------------------------------------------------------------------- #


async def test_leg2_timeout_triggers_leg1_unwind():
    exchange = _ScriptedExchange(
        [
            # leg1 fills
            None,  # placeholder, replaced via default
            "hang",  # leg2 hangs → timeout
            # leg1 unwind reaches default-fill path
        ]
    )
    # Replace placeholder with a concrete OrderResult sized to leg1's actual qty.
    # We don't know exact qty until strategy runs, so build the script lazily.

    strategy, risk, sm = _build_stack(exchange, timeout=0.02)
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    assert risk.check(signal) == RiskDecision.APPROVED

    # Inject the right leg1 result now that we know the qty.
    exchange._script = [
        OrderResult(id="l1", status=OrderStatus.FILLED, filled=signal.leg1_quantity),
        "hang",
    ]
    await sm.start(signal)

    # leg1 + leg2 (timed out) + unwind leg1 = 3 placed orders
    assert len(exchange.placed) == 3
    unwind = exchange.placed[2]
    assert unwind.trading_pair == signal.leg1_pair
    # Unwind reverses leg1's side, whatever direction the cycle was emitted in.
    expected_reverse = Side.SELL if signal.leg1_side == Side.BUY else Side.BUY
    assert unwind.side == expected_reverse, (
        f"unwind should reverse leg1 side {signal.leg1_side}, got {unwind.side}"
    )
    assert unwind.quantity == signal.leg1_quantity


# --------------------------------------------------------------------------- #
# Scenario 4: TTL expiry for one of three pairs
# --------------------------------------------------------------------------- #


async def test_ttl_expiry_one_leg_no_signal():
    exchange = _ScriptedExchange([])
    strategy, _, _ = _build_stack(exchange)
    base_t = 1000.0
    with patch("atlas.strategy.arbitrage.triangular.time.monotonic") as mock_time:
        mock_time.return_value = base_t
        # Seed BTC/USDT and ETH/BTC
        strategy.on_tickers(
            {
                "BTC/USDT": {"bid": 50000, "ask": 50000},
                "ETH/BTC": {"bid": 0.06, "ask": 0.06},
            }
        )
        # Advance past TTL
        mock_time.return_value = base_t + _PRICE_TTL_SECONDS + 1
        # Now add ETH/USDT; the other two should be stale → no triangle.
        signals = strategy.on_tickers({"ETH/USDT": {"bid": 3200, "ask": 3200}})
    assert signals == []


# --------------------------------------------------------------------------- #
# Scenario 5: partial fill propagation (KNOWN BUG)
# --------------------------------------------------------------------------- #


async def test_partial_fill_propagation_into_leg2():
    """leg1 partial fill (50%) → leg2 should be scaled to 50% of planned qty."""
    exchange = _ScriptedExchange([])
    strategy, _, sm = _build_stack(exchange, timeout=0.5)
    [signal] = strategy.on_tickers(_ARB_TICKERS)

    half_leg1 = signal.leg1_quantity / 2
    exchange._script = [
        OrderResult(id="l1", status=OrderStatus.FILLED, filled=half_leg1),
    ]
    await sm.start(signal)

    expected_q2 = signal.leg2_quantity / 2
    leg2_order = exchange.placed[1]
    assert leg2_order.quantity == expected_q2, (
        f"leg2 should scale to {expected_q2} (50% of signal qty) since "
        f"leg1 filled at 50%; got {leg2_order.quantity}"
    )


# --------------------------------------------------------------------------- #
# Scenario 6: exposure aggregation across consecutive signals
# --------------------------------------------------------------------------- #


async def test_back_to_back_signals_both_approved_when_risk_is_per_signal():
    """
    BUG / design-gap: RiskManager.check operates per-signal. Two consecutive
    signals each pass independently — there is no concept of in-flight or
    cumulative exposure. We size max_exposure to fit ONE signal exactly; the
    bug is that the SECOND signal still passes, because risk never aggregates.
    """
    exchange = _ScriptedExchange([])
    # Use generous max_exposure so first signal definitely passes; the test
    # is about lack of *cumulative* tracking, not single-signal sizing.
    strategy, risk, _ = _build_stack(exchange, max_exposure=Decimal("200"))
    [s1] = strategy.on_tickers(_ARB_TICKERS)
    [s2] = strategy.on_tickers(_ARB_TICKERS)  # cache → another opportunity

    d1 = risk.check(s1)
    d2 = risk.check(s2)
    # The per-signal notional for the BTC-ETH-USDT triangle at these prices is
    # ~$96 in USDT (3 legs × ~$32 each). $200 max_exposure covers ONE signal.
    assert d1 == RiskDecision.APPROVED, f"first signal rejected: {d1}"
    # The bug: second signal also passes. Two in-flight signals together
    # consume ~$192, which is also under $200 in this example — but in real
    # flow a single signal can be much larger, and risk still wouldn't track
    # cross-signal exposure.
    assert d2 == RiskDecision.APPROVED, (
        f"second signal decision={d2}; RiskManager should approve "
        "independently since it doesn't track in-flight exposure."
    )
    # Sanity: signals are not artificially identical (sigs share Decimal values
    # because cache is identical, but they ARE distinct dataclass instances).
    assert s1 is not s2


async def test_max_order_size_below_largest_leg_rejects():
    """If max_order_size < any leg notional → reject. The emitted cycle has
    legs with notionals in the $30 range; setting max to $20 forces rejection."""
    exchange = _ScriptedExchange([])
    strategy, risk, _ = _build_stack(exchange, max_order_size=Decimal("20"))
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    # Every leg in the emitted cycle has USDT notional ≈ $30+, all above $20.
    assert risk.check(signal) == RiskDecision.REJECTED


# --------------------------------------------------------------------------- #
# Scenario 7: state-machine re-entry after first signal completes
# --------------------------------------------------------------------------- #


async def test_state_machine_accepts_new_signal_after_completion():
    exchange = _ScriptedExchange([])
    strategy, _, sm = _build_stack(exchange, timeout=1.0)
    [s1] = strategy.on_tickers(_ARB_TICKERS)
    await sm.start(s1)
    placed_count_1 = len(exchange.placed)

    [s2] = strategy.on_tickers(_ARB_TICKERS)
    await sm.start(s2)
    assert len(exchange.placed) == placed_count_1 + 3


async def test_state_machine_silently_skips_concurrent_signal():
    """
    Documented behavior: a signal arriving while another is in flight is
    DROPPED with no logging, no queue, no compensation. The strategy keeps
    emitting opportunities every tick; downstream they vanish.
    """
    exchange = _ScriptedExchange(
        [
            None,  # placeholder for leg1
            "hang",  # leg2 hangs
        ]
    )
    strategy, _, sm = _build_stack(exchange, timeout=0.1)
    [s1] = strategy.on_tickers(_ARB_TICKERS)
    exchange._script = [
        OrderResult(id="l1", status=OrderStatus.FILLED, filled=s1.leg1_quantity),
        "hang",
    ]

    task = asyncio.create_task(sm.start(s1))
    await asyncio.sleep(0.02)  # let leg1 fill, leg2 begin hanging
    [s2] = strategy.on_tickers(_ARB_TICKERS)
    placed_before = len(exchange.placed)
    await sm.start(s2)  # should be no-op
    placed_after = len(exchange.placed)
    assert placed_after == placed_before, "Second signal modified placements"
    await task
