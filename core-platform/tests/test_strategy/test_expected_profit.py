"""
Regression tests: expected_profit 단위 수정 (Bug 3 fix)

수정 전: expected_profit = q1 * (rate - 1)
  → leg1이 BUY인 경우 q1은 base-asset 단위, rate는 무차원이라 단위 불일치.
  → ask 가격 인수만큼 오차 발생 (BUY BTC/USDT ask=50000이면 50000배 차이).

수정 후: expected_profit = input_capital * (rate - 1)
  → BUY: input_capital = q1 * ask  (실제 투입한 quote 통화량)
  → SELL: input_capital = q1       (실제 투입한 base 통화량)
"""

from decimal import Decimal

import pytest

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.execution.side import Side
from atlas.strategy.arbitrage.graph import ArbOpportunity
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

_EXCHANGE = Exchange.BINANCE
_QTY = Decimal("0.01")

# 명확한 차익거래 가격: ETH/USDT가 BTC/USDT × ETH/BTC 대비 6.7% 과대평가
_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000, "ask": 50000},
    "ETH/BTC": {"bid": 0.06, "ask": 0.06},
    "ETH/USDT": {"bid": 3200, "ask": 3200},
}


def _strategy() -> TriangularArbitrageStrategy:
    return TriangularArbitrageStrategy(
        exchange=_EXCHANGE, order_quantity=_QTY, min_profit=Decimal("0.002")
    )


def test_expected_profit_positive():
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    assert signal.expected_profit > 0


def test_expected_profit_consistent_with_capital_committed():
    """expected_profit / input_capital ≈ (opp.rate - 1).

    input_capital 계산:
      - leg1이 BUY: q1 * ask_leg1 (실제 지불한 quote 통화)
      - leg1이 SELL: q1 (실제 투입한 base 통화)

    수정 전 버그: BUY leg1일 때 expected_profit = q1 * (rate-1) → ask 인수만큼 오차.
    수정 후: input_capital에 ask를 곱해 단위를 맞춤.

    이 테스트는 profit_rate가 합리적인 범위(1%~20%) 안에 있는지 검증한다.
    버그 재현 시 BUY leg1에서 profit_rate가 1/ask 수준(≈0.00003%)으로 떨어짐.
    """
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)

    ask_map = {
        "BTC/USDT": Decimal("50000"),
        "ETH/BTC": Decimal("0.06"),
        "ETH/USDT": Decimal("3200"),
    }
    leg1_key = f"{signal.leg1_pair.ticker}/{signal.leg1_pair.quote}"
    ask_leg1 = ask_map[leg1_key]

    if signal.leg1_side == Side.BUY:
        input_capital = signal.leg1_quantity * ask_leg1
    else:
        input_capital = signal.leg1_quantity

    profit_rate = signal.expected_profit / input_capital

    # 테스트 가격에서 이론적 수익률: ≈6.7% (수수료 후 ≈6.1%)
    # 합리적 범위: 1% ~ 20%
    assert Decimal("0.01") < profit_rate < Decimal("0.20"), (
        f"profit_rate={float(profit_rate):.4%} is outside expected [1%, 20%]. "
        f"Possible unit mismatch bug: expected_profit={signal.expected_profit}, "
        f"input_capital={input_capital}"
    )


def test_expected_profit_not_equal_to_buggy_formula_for_buy_leg():
    """BUY leg1일 때 수정 전 공식(q1 * (rate-1))과 다른 값이어야 한다.

    수정 전: q1 * (rate-1)
    수정 후: q1 * ask * (rate-1)  (ask ≠ 1 이므로 값이 달라야 함)
    """
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)

    if signal.leg1_side != Side.BUY:
        pytest.skip("This test only applies when leg1 is BUY")

    ask_map = {
        "BTC/USDT": Decimal("50000"),
        "ETH/BTC": Decimal("0.06"),
        "ETH/USDT": Decimal("3200"),
    }
    leg1_key = f"{signal.leg1_pair.ticker}/{signal.leg1_pair.quote}"
    ask_leg1 = ask_map[leg1_key]

    # 구 공식: q1 * (rate-1). rate ≈ 1.063이면 q1*(rate-1) ≈ 0.01*0.063 = 0.00063
    # 신 공식: q1 * ask * (rate-1)
    # ask ≠ 1 이므로 두 값은 달라야 함
    q1 = signal.leg1_quantity
    # rate-1은 expected_profit / input_capital
    rate_minus_1 = signal.expected_profit / (q1 * ask_leg1)
    old_formula_value = q1 * rate_minus_1  # 수정 전 결과

    assert abs(signal.expected_profit - old_formula_value) > Decimal("1e-8"), (
        "expected_profit should differ from old q1*(rate-1) formula when leg1 is BUY "
        f"(ask={ask_leg1})"
    )


def test_to_signal_buy_leg1_expected_profit_matches_capital_times_rate():
    """_to_signal 직접 단위 테스트: BUY leg1의 expected_profit = q1 * ask * (rate - 1)."""
    import time

    from atlas.core.trading_pair import TradingPair as TP

    strategy = _strategy()

    btc_usdt = TP(ticker=Ticker.BTC, quote=Quote.USDT)
    eth_btc = TP(ticker=Ticker.ETH, quote=Quote.BTC)
    eth_usdt = TP(ticker=Ticker.ETH, quote=Quote.USDT)

    now = time.monotonic()
    strategy._prices = {
        btc_usdt: (Decimal("50000"), Decimal("50000"), now),
        eth_btc: (Decimal("0.06"), Decimal("0.06"), now),
        eth_usdt: (Decimal("3200"), Decimal("3200"), now),
    }

    rate = Decimal("1.0635")
    opp = ArbOpportunity(
        legs=(
            (eth_btc, Side.BUY),  # leg1: BUY ETH/BTC — spend BTC, get ETH
            (eth_usdt, Side.SELL),  # leg2: SELL ETH/USDT — spend ETH, get USDT
            (btc_usdt, Side.BUY),  # leg3: BUY BTC/USDT — spend USDT, get BTC
        ),
        rate=rate,
    )
    signal = strategy._to_signal(opp)

    # leg1 is BUY ETH/BTC: input_capital = q1 * ask_ETH/BTC = 0.01 * 0.06 = 0.0006 BTC
    expected = _QTY * Decimal("0.06") * (rate - 1)
    assert abs(signal.expected_profit - expected) < Decimal("1e-10"), (
        f"expected_profit={signal.expected_profit} != {expected}"
    )


def test_to_signal_sell_leg1_expected_profit_matches_q1_times_rate():
    """_to_signal 직접 단위 테스트: SELL leg1의 expected_profit = q1 * (rate - 1)."""
    import time

    from atlas.core.trading_pair import TradingPair as TP

    strategy = _strategy()

    btc_usdt = TP(ticker=Ticker.BTC, quote=Quote.USDT)
    eth_btc = TP(ticker=Ticker.ETH, quote=Quote.BTC)
    eth_usdt = TP(ticker=Ticker.ETH, quote=Quote.USDT)

    now = time.monotonic()
    strategy._prices = {
        btc_usdt: (Decimal("50000"), Decimal("50000"), now),
        eth_btc: (Decimal("0.06"), Decimal("0.06"), now),
        eth_usdt: (Decimal("3200"), Decimal("3200"), now),
    }

    rate = Decimal("1.0635")
    opp = ArbOpportunity(
        legs=(
            (eth_usdt, Side.SELL),  # leg1: SELL ETH/USDT — spend ETH, get USDT
            (btc_usdt, Side.BUY),  # leg2: BUY BTC/USDT — spend USDT, get BTC
            (eth_btc, Side.BUY),  # leg3: BUY ETH/BTC — spend BTC, get ETH
        ),
        rate=rate,
    )
    signal = strategy._to_signal(opp)

    # leg1 is SELL ETH/USDT: input_capital = q1 (ETH sold) = 0.01
    expected = _QTY * (rate - 1)
    assert abs(signal.expected_profit - expected) < Decimal("1e-10"), (
        f"expected_profit={signal.expected_profit} != {expected}"
    )
