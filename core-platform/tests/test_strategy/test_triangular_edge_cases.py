"""
Edge-case tests for the triangular arbitrage strategy and Bellman-Ford graph search.

These tests intentionally target known weak spots in the current logic:
  * crossed-book (bid > ask) on a single pair → spurious negative cycle
  * exact min_profit boundary
  * TTL expiry of partial triangle data
  * extreme magnitude prices (BTC-scale vs altcoin-scale)
  * fee neutrality not modelled inside detect_arbitrage
  * dueling triangles (multiple opportunities in same tick batch)
  * 2-node cycles (BUY-then-SELL same pair when crossed)
  * exact bid==ask (zero-spread) round-trip → expect no profit

Most tests use real graph and propagation logic; only `time.monotonic` for TTL
is patched where required. Tests that EXPOSE BUGS in the current code are
marked with comments tagged `BUG:`.
"""

from __future__ import annotations

import math
import time
from decimal import Decimal
from unittest.mock import patch

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side
from atlas.strategy.arbitrage.graph import detect_arbitrage
from atlas.strategy.arbitrage.triangular import (
    _PRICE_TTL_SECONDS,
    TriangularArbitrageStrategy,
)

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)
_BNB_USDT = TradingPair(ticker=Ticker.BNB, quote=Quote.USDT)
_BNB_BTC = TradingPair(ticker=Ticker.BNB, quote=Quote.BTC)


def _p(bid: str, ask: str) -> tuple[Decimal, Decimal]:
    return Decimal(bid), Decimal(ask)


def _strategy(min_profit: Decimal = Decimal("0.002")) -> TriangularArbitrageStrategy:
    return TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0.01"),
        min_profit=min_profit,
    )


# --------------------------------------------------------------------------- #
# 1. GRAPH-LEVEL EDGE CASES
# --------------------------------------------------------------------------- #


def test_crossed_book_single_pair_creates_spurious_arb():
    """
    BUG (likely): when bid > ask on a single pair, the graph contains two edges
    BTC→USDT (weight=-log(bid)) and USDT→BTC (weight=+log(ask)). Their sum is
    log(ask) - log(bid) < 0, so a 2-node cycle exists with no fees modelled.
    The current detect_arbitrage builds both edges without sanity checking
    bid <= ask, so it will report a profitable opportunity on bad market data.
    """
    # bid (50100) > ask (50000) → crossed book (data corruption / stale feed)
    prices = {_BTC_USDT: _p("50100", "50000")}
    result = detect_arbitrage(prices)
    # If this passes (result is None), the graph is robust. If it returns an
    # opportunity, the code happily exploits broken data.
    assert result is None, (
        f"Spurious arb detected on crossed book: rate={result.rate if result else None}"
    )


def test_zero_spread_three_pairs_round_trip_exactly_one():
    """bid==ask everywhere, fair prices → product is exactly 1.0, no arb."""
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("4000", "4000"),
        _ETH_BTC: _p("0.08", "0.08"),
    }
    assert detect_arbitrage(prices) is None


def test_min_profit_boundary_exact_match_not_filtered_at_graph_level():
    """detect_arbitrage doesn't know about min_profit; it returns any cycle > 1.0.
    The strategy layer is responsible for the threshold."""
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3900", "3900"),
        _ETH_BTC: _p("0.075", "0.075"),
    }
    result = detect_arbitrage(prices)
    assert result is not None
    assert result.rate > 1


def test_extreme_small_price_altcoin_handled():
    """Prices like 1e-8 (sat-priced altcoin) shouldn't blow up log() or overflow."""
    # Construct an arb between BNB/USDT, BNB/BTC, BTC/USDT with very small ratios.
    prices = {
        _BTC_USDT: _p("60000", "60000"),
        _BNB_USDT: _p("600", "600"),
        _BNB_BTC: _p("0.0099", "0.0099"),  # fair value = 0.01 → 1% underpriced
    }
    result = detect_arbitrage(prices)
    assert result is not None
    # Round-trip: 1 USDT → 1/600 BNB → 1/600 * 0.0099 BTC → 1/600*0.0099*60000 USDT = 0.99 < 1?
    # Direction matters; BF picks the profitable side. Just sanity-check finiteness.
    assert math.isfinite(float(result.rate))


def test_extreme_large_price_btc_scale_handled():
    """Trillion-dollar BTC shouldn't overflow Decimal/float conversion."""
    prices = {
        _BTC_USDT: _p("1000000000", "1000000000"),  # 1B USDT/BTC
        _ETH_USDT: _p("78000000", "78000000"),
        _ETH_BTC: _p("0.075", "0.075"),
    }
    result = detect_arbitrage(prices)
    # rate = (1/1e9)*(1/0.075)*7.8e7 = 7.8e7 / 7.5e7 = 1.04
    assert result is not None
    assert float(result.rate) > 1.0
    assert math.isfinite(float(result.rate))


def test_zero_ask_excludes_buy_edge():
    """ask==0 must not produce a BUY edge (would otherwise be log(0) = -inf)."""
    prices = {_BTC_USDT: _p("50000", "0")}
    # No arb possible: only SELL edge exists, single pair → no cycle.
    assert detect_arbitrage(prices) is None


def test_zero_bid_excludes_sell_edge():
    """bid==0 must not produce a SELL edge."""
    prices = {_BTC_USDT: _p("0", "50000")}
    assert detect_arbitrage(prices) is None


def test_single_node_graph_returns_none():
    """Single node has no edges → no cycle possible."""
    # Empty prices but pass through code path
    assert detect_arbitrage({}) is None


def test_two_simultaneous_arb_triangles_returns_one_opportunity():
    """
    BTC-ETH-USDT triangle AND BTC-BNB-USDT triangle both contain profit.
    detect_arbitrage returns the FIRST cycle it finds. Document this — there's
    no guarantee about which one wins.
    """
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3900", "3900"),  # ETH/BTC fair 0.078 → 0.075 → ~4% arb
        _ETH_BTC: _p("0.075", "0.075"),
        _BNB_USDT: _p("600", "600"),
        _BNB_BTC: _p("0.011", "0.011"),  # fair 0.012 → ~9% arb
    }
    result = detect_arbitrage(prices)
    assert result is not None
    assert result.rate > 1


def test_eps_boundary_exact_round_trip():
    """
    Round-trip rate exactly 1.0 (log-sum = 0) must not trigger the
    `dist[u] + w < dist[v] - _EPS` strict-less comparison.
    """
    # bid==ask, ratios that compound to exactly 1.0 in Decimal-land
    # (BTC/USDT=2, ETH/BTC=2, ETH/USDT=4) → all integers, no float drift
    btc_usdt = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
    eth_usdt = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)
    eth_btc = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)
    prices = {
        btc_usdt: _p("2", "2"),
        eth_btc: _p("2", "2"),
        eth_usdt: _p("4", "4"),
    }
    # Round-trip: USDT→BTC: 1/2, →ETH: 1/2 * 1/2 = 1/4, →USDT: 4 * 1/4 = 1.0
    # No profit; must return None
    assert detect_arbitrage(prices) is None


# --------------------------------------------------------------------------- #
# 2. STRATEGY-LEVEL PRICE UPDATE EDGE CASES
# --------------------------------------------------------------------------- #


def test_ttl_expired_pair_skips_triangle():
    """One leg expires past TTL → triangle skipped, no signal emitted."""
    strategy = _strategy()
    base_t = 1000.0
    with patch("atlas.strategy.arbitrage.triangular.time.monotonic") as mock_time:
        mock_time.return_value = base_t
        strategy.on_tickers(
            {
                "BTC/USDT": {"bid": 50000, "ask": 50000},
                "ETH/BTC": {"bid": 0.06, "ask": 0.06},
            }
        )
        # Advance time past TTL for the first two pairs.
        mock_time.return_value = base_t + _PRICE_TTL_SECONDS + 0.001
        signals = strategy.on_tickers({"ETH/USDT": {"bid": 3200, "ask": 3200}})
    assert signals == []


def test_ttl_at_exact_boundary_still_fresh():
    """TTL boundary uses <=, so exactly TTL seconds should still be fresh."""
    strategy = _strategy()
    base_t = 1000.0
    with patch("atlas.strategy.arbitrage.triangular.time.monotonic") as mock_time:
        mock_time.return_value = base_t
        strategy.on_tickers(
            {
                "BTC/USDT": {"bid": 50000, "ask": 50000},
                "ETH/BTC": {"bid": 0.06, "ask": 0.06},
            }
        )
        # Advance time to EXACTLY TTL → still <= TTL → still fresh.
        mock_time.return_value = base_t + _PRICE_TTL_SECONDS
        signals = strategy.on_tickers({"ETH/USDT": {"bid": 3200, "ask": 3200}})
    assert len(signals) == 1


def test_crossed_book_tickers_not_rejected_by_strategy():
    """
    The strategy's _update_prices stores any pair where `bid and ask` are truthy.
    It does NOT validate bid <= ask. The crossed-book data is fed into
    detect_arbitrage, which finds a 2-node cycle (BUY then SELL the same pair).
    _to_signal then crashes with `ValueError: Expected 3-leg opportunity, got 2`.

    This is a real bug with TWO symptoms:
      1. Crossed-book data is accepted (it should be filtered)
      2. The exception crashes the tick handler instead of being caught

    A correct implementation would either:
      a) drop bid>ask data in _update_prices, OR
      b) constrain detect_arbitrage to require cycle_len == triangle size.
    """
    strategy = _strategy(min_profit=Decimal("0.0001"))  # tiny threshold
    tickers = {
        "BTC/USDT": {"bid": 50100, "ask": 50000},  # crossed!
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3000, "ask": 3000},
    }
    # The strategy must not raise on bad market data; the tick loop has no
    # exception handler. Assert NO signal AND NO exception.
    try:
        signals = strategy.on_tickers(tickers)
    except Exception as e:
        raise AssertionError(
            f"on_tickers crashed on crossed-book data: {type(e).__name__}: {e}. "
            "The tick handler has no exception barrier — this kills the runner."
        ) from e
    assert signals == [], (
        f"Crossed-book data slipped through strategy and produced "
        f"{len(signals)} signal(s); strategy must reject bid > ask."
    )


def test_negative_price_not_ingested():
    """A negative price (data corruption) should never produce a tradeable signal."""
    strategy = _strategy()
    # Negative bid is truthy in Python; Decimal("-1") is also truthy.
    # The strategy must guard against this; otherwise log() of a negative number
    # will raise inside detect_arbitrage.
    tickers = {
        "BTC/USDT": {"bid": -50000, "ask": 50000},
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3200, "ask": 3200},
    }
    # Either reject the price or emit no signal — but never crash with ValueError.
    try:
        signals = strategy.on_tickers(tickers)
    except ValueError as e:
        # math.log() on a negative number raises ValueError. This is a bug:
        # the strategy should sanitise inputs before passing them to graph.
        raise AssertionError(f"Strategy crashed on negative price: {e}") from e
    assert signals == []


def test_zero_quantity_not_yet_a_concern_quantities_propagated_from_decimal():
    """
    _compute_quantities returns Decimal arithmetic; with base_qty=0 every leg
    would be 0. The graph itself doesn't care about quantity (only prices).
    This documents that a strategy with order_quantity=0 emits 0-qty signals.
    """
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0"),
        min_profit=Decimal("0.002"),
    )
    tickers = {
        "BTC/USDT": {"bid": 50000, "ask": 50000},
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3200, "ask": 3200},
    }
    signals = strategy.on_tickers(tickers)
    # Either no signals (sane) OR signals with leg_quantity == 0 (current behaviour).
    if signals:
        for s in signals:
            # All quantities zero → unfillable order; engine/state should reject.
            assert s.leg1_quantity == 0 and s.leg2_quantity == 0 and s.leg3_quantity == 0


# --------------------------------------------------------------------------- #
# 3. QUANTITY PROPAGATION EDGE CASES
# --------------------------------------------------------------------------- #


def test_compute_quantities_buy_sell_buy_cycle():
    """USDT→BTC→ETH→USDT cycle: BUY BTC/USDT → BUY ETH/BTC → SELL ETH/USDT.
    Direction USDT → BTC → ETH → USDT means:
      leg1: BUY BTC/USDT (spend USDT, receive BTC)
      leg2: BUY ETH/BTC (spend BTC, receive ETH)
      leg3: SELL ETH/USDT (spend ETH, receive USDT)
    """
    strategy = _strategy()
    [signal] = strategy.on_tickers(
        {
            "BTC/USDT": {"bid": 50000, "ask": 50000},
            "ETH/BTC": {"bid": 0.06, "ask": 0.06},
            "ETH/USDT": {"bid": 3200, "ask": 3200},  # >fair value 3000
        }
    )
    # The detected cycle is USDT→BTC→ETH→USDT or USDT→ETH→BTC→USDT depending
    # on which has a negative log-sum. With ETH/USDT overpriced (3200 vs fair
    # 3000), the profitable direction is BUY BTC → BUY ETH (in BTC) → SELL ETH
    # (in USDT). Walk through expected quantities:
    base = Decimal("0.01")  # leg1 BTC quantity
    expected_q1 = base

    sides = (signal.leg1_side, signal.leg2_side, signal.leg3_side)
    # Document the actual emitted cycle so failures are diagnosable.
    assert signal.leg1_quantity == expected_q1, (
        f"leg1 qty mismatch: got {signal.leg1_quantity}, sides={sides}"
    )
    # Sanity: all positive
    assert signal.leg2_quantity > 0
    assert signal.leg3_quantity > 0


def test_compute_quantities_consistent_with_round_trip():
    """
    Quantities should chain: fee-adjusted output of leg N feeds input of leg N+1.
    BUY output = base_qty*(1-fee), SELL output = base_qty*bid*(1-fee). The next
    leg's base-asset qty = output/ask (BUY) or output (SELL).
    """
    fee = Decimal("0.001")
    strategy = _strategy()
    [signal] = strategy.on_tickers(
        {
            "BTC/USDT": {"bid": 50000, "ask": 50000},
            "ETH/BTC": {"bid": 0.06, "ask": 0.06},
            "ETH/USDT": {"bid": 3200, "ask": 3200},
        }
    )

    legs = [
        (signal.leg1_pair, signal.leg1_side, signal.leg1_quantity),
        (signal.leg2_pair, signal.leg2_side, signal.leg2_quantity),
        (signal.leg3_pair, signal.leg3_side, signal.leg3_quantity),
    ]
    # All three quantities must be strictly positive.
    assert all(q > 0 for *_, q in legs)

    prices = {
        _BTC_USDT: Decimal("50000"),
        _ETH_BTC: Decimal("0.06"),
        _ETH_USDT: Decimal("3200"),
    }
    for i in range(2):
        pair_i, side_i, q_i = legs[i]
        pair_n, side_n, q_n_actual = legs[i + 1]
        p_i = prices[pair_i]
        # fee-adjusted output of leg i
        out = q_i * (1 - fee) if side_i == Side.BUY else q_i * p_i * (1 - fee)
        p_n = prices[pair_n]
        expected_q_next = out / p_n if side_n == Side.BUY else out
        assert abs(q_n_actual - expected_q_next) < Decimal("0.0001"), (
            f"leg{i + 2} qty chain broken: got {q_n_actual}, "
            f"expected {expected_q_next} (delta={abs(q_n_actual - expected_q_next)})"
        )


def test_zero_ask_breaks_input_to_base_qty():
    """
    BUG (potential): _compute_quantities calls `input_amount / ask` for BUY legs.
    If a pair has ask==0 in the cache (shouldn't happen since _update_prices
    filters), division-by-zero would raise. _build_edges skips ask==0, so
    detect_arbitrage never returns a cycle that includes such a leg. This test
    documents the safety: if a cycle is returned, all its legs must have ask>0.
    """
    strategy = _strategy()
    # Manually poison the cache with ask==0 for one pair, then ensure no signal.
    # We use the strategy's internal `_prices` to simulate stale/corrupted data.
    strategy._prices[_BTC_USDT] = (Decimal("50000"), Decimal("0"), time.monotonic())
    strategy._prices[_ETH_BTC] = (Decimal("0.06"), Decimal("0.06"), time.monotonic())
    strategy._prices[_ETH_USDT] = (Decimal("3200"), Decimal("3200"), time.monotonic())

    # Trigger detection by passing a dummy tickers dict (won't overwrite, since
    # _update_prices requires both bid and ask truthy).
    signals = strategy.on_tickers({})
    # If a cycle is somehow constructed despite ask==0, quantities computation
    # will blow up. The proper behaviour: skip the corrupted pair.
    for s in signals:
        # If any signal is emitted, leg quantities must be finite Decimal > 0.
        assert s.leg1_quantity > 0
        assert s.leg2_quantity > 0
        assert s.leg3_quantity > 0


def test_fees_not_accounted_for_in_rate():
    """
    Fee-aware Bellman-Ford correctly rejects a ~0.3% gross arb that is unprofitable
    after 3 legs × 0.1% taker fee.

    With fees baked into edge weights, a 0.3% gross cycle yields a net rate < 1.0
    and detect_arbitrage returns None — no false-positive signal.
    """
    # Construct a triangle with ~0.3% gross arb — less than 3 × 0.1% taker fee.
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_BTC: _p("0.06", "0.06"),
        _ETH_USDT: _p("3009", "3009"),  # fair = 3000, so ~0.3% gross arb
    }
    result = detect_arbitrage(prices)
    # Fee-aware graph finds no profitable cycle: gross profit ≈ fees.
    assert result is None, (
        f"detect_arbitrage returned rate={result.rate if result else None} for a "
        "barely-profitable arb that fees should eliminate."
    )
