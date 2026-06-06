from decimal import Decimal

import pytest

from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side
from atlas.strategy.arbitrage.graph import detect_arbitrage

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)


def _p(bid: str, ask: str) -> tuple[Decimal, Decimal]:
    return Decimal(bid), Decimal(ask)


def _leg_currencies(pair: TradingPair, side: Side) -> tuple[str, str]:
    base, quote = str(pair.ticker), str(pair.quote)
    return (quote, base) if side == Side.BUY else (base, quote)


def _is_valid_cycle(legs: tuple) -> bool:
    currencies = [_leg_currencies(p, s) for p, s in legs]
    for i, (_, to) in enumerate(currencies):
        from_next, _ = currencies[(i + 1) % len(currencies)]
        if to != from_next:
            return False
    return True


# ---------------------------------------------------------------------------


def test_empty_prices_returns_none():
    assert detect_arbitrage({}) is None


def test_single_pair_no_arb_spread_kills_profit():
    # round-trip: 1 USDT → 1/50000 BTC → 49990 USDT/BTC * 1/50000 = 0.9998 USDT
    assert detect_arbitrage({_BTC_USDT: _p("49990", "50000")}) is None


def test_three_pairs_fair_prices_no_arb():
    # USDT→BTC→ETH→USDT: (1/50000)*(1/0.082)*3900 = 3900/4100 ≈ 0.951 < 1
    # USDT→ETH→BTC→USDT: (1/4000)*0.078*49000        ≈ 0.955 < 1
    prices = {
        _BTC_USDT: _p("49000", "50000"),
        _ETH_USDT: _p("3900", "4000"),
        _ETH_BTC: _p("0.078", "0.082"),
    }
    assert detect_arbitrage(prices) is None


def test_triangular_arb_usdt_btc_eth_usdt():
    # USDT→BTC→ETH→USDT gross rate = 3900/3750 = 1.04
    # After 3 legs × 0.1% taker fee: net ≈ 1.04 * (1-0.001)^3 ≈ 1.0369
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3900", "3900"),
        _ETH_BTC: _p("0.075", "0.075"),
    }
    result = detect_arbitrage(prices)
    assert result is not None
    assert result.rate > 1
    assert result.rate < Decimal("1.04")  # fee-adjusted rate is below gross rate
    assert _is_valid_cycle(result.legs)


def test_triangular_arb_usdt_eth_btc_usdt():
    # USDT→ETH→BTC→USDT: (1/3800)*0.08*50000 = 4000/3800 ≈ 1.052
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3800", "3800"),
        _ETH_BTC: _p("0.08", "0.08"),
    }
    result = detect_arbitrage(prices)
    assert result is not None
    assert result.rate > 1
    assert _is_valid_cycle(result.legs)


def test_arb_legs_count_equals_currencies_in_cycle():
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3900", "3900"),
        _ETH_BTC: _p("0.075", "0.075"),
    }
    result = detect_arbitrage(prices)
    assert result is not None
    assert len(result.legs) == 3  # 3-node cycle → 3 legs


def test_no_arb_when_all_rates_exactly_one():
    # bid == ask, perfectly efficient market: round-trip = 1.0 exactly
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("4000", "4000"),
        _ETH_BTC: _p("0.08", "0.08"),
    }
    # rate = (1/50000)*(1/0.08)*4000 = 4000/4000 = 1.0 — no profit
    assert detect_arbitrage(prices) is None


def test_disconnected_one_way_pair_does_not_index_error():
    # Single pair with only ask>0 (no bid) used to trigger pred[node][0] IndexError
    # because dist[] was uniformly 0.0 and any negative weight could mark a node
    # whose pred chain was None. Now we rely on a virtual-source initialisation,
    # so a one-way single edge cannot form a cycle and should return None cleanly.
    pair = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
    assert detect_arbitrage({pair: _p("0", "50000")}) is None


def test_arb_opportunity_is_frozen():
    prices = {
        _BTC_USDT: _p("50000", "50000"),
        _ETH_USDT: _p("3900", "3900"),
        _ETH_BTC: _p("0.075", "0.075"),
    }
    result = detect_arbitrage(prices)
    assert result is not None
    with pytest.raises(Exception):
        result.rate = Decimal("1")  # type: ignore[misc]
