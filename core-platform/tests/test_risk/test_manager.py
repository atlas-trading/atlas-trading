from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.side import Side
from atlas.risk.manager import RiskDecision, RiskManager

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)

# All risk limits below are in USDT notional. With BTC=$50000, ETH=$3000,
# 0.01 BTC ≈ $500 and 0.01 ETH ≈ $30.
_USDT_PRICES = {
    _BTC_USDT: Decimal("50000"),
    _ETH_USDT: Decimal("3000"),
}


def _make_signal(qty: Decimal = Decimal("0.01")) -> ArbSignal:
    return ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_BTC_USDT,
        leg1_side=Side.BUY,
        leg1_quantity=qty,
        leg2_pair=_ETH_USDT,
        leg2_side=Side.BUY,
        leg2_quantity=qty,
        leg3_pair=_BTC_USDT,
        leg3_side=Side.SELL,
        leg3_quantity=qty,
        expected_profit=Decimal("5"),
    )


def _make_rm(
    max_order_size: Decimal = Decimal("10000"),
    max_exposure: Decimal = Decimal("100000"),
) -> RiskManager:
    rm = RiskManager(max_order_size=max_order_size, max_exposure=max_exposure)
    rm.update_prices(_USDT_PRICES)
    return rm


def test_approved_within_limits():
    # leg1 notional = 0.01 * 50000 = 500 USDT, leg2 = 30 USDT, leg3 = 500 USDT.
    # Per-order max = 10000 USDT, total exposure max = 100000 USDT → APPROVED.
    rm = _make_rm()
    assert rm.check(_make_signal()) == RiskDecision.APPROVED


def test_rejected_kill_switch():
    rm = _make_rm()
    rm.set_kill_switch(True)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_rejected_not_connected():
    rm = _make_rm()
    rm.set_connected(False)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_rejected_order_size_exceeded():
    # 0.01 BTC = 500 USDT, set max_order_size to 100 → REJECTED.
    rm = _make_rm(max_order_size=Decimal("100"))
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_rejected_exposure_exceeded():
    # Total notional ≈ 500 + 30 + 500 = 1030 USDT, set max_exposure to 100.
    rm = _make_rm(max_exposure=Decimal("100"))
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_kill_switch_toggle():
    rm = _make_rm()
    rm.set_kill_switch(True)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED
    rm.set_kill_switch(False)
    assert rm.check(_make_signal()) == RiskDecision.APPROVED


def test_reconnect_resumes():
    rm = _make_rm()
    rm.set_connected(False)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED
    rm.set_connected(True)
    assert rm.check(_make_signal()) == RiskDecision.APPROVED


def test_rejected_when_price_missing_for_leg():
    # No USDT prices loaded → cannot value any leg → REJECTED.
    rm = RiskManager(max_order_size=Decimal("1e9"), max_exposure=Decimal("1e9"))
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_cross_pair_leg_priced_via_base_usdt():
    # A leg on ETH/BTC needs ETH/USDT to value it. With ETH=$3000 and
    # quantity=0.5 ETH, notional ≈ 1500 USDT.
    rm = _make_rm(max_order_size=Decimal("2000"), max_exposure=Decimal("5000"))
    signal = ArbSignal(
        exchange=Exchange.BINANCE,
        leg1_pair=_BTC_USDT,
        leg1_side=Side.BUY,
        leg1_quantity=Decimal("0.01"),
        leg2_pair=_ETH_BTC,
        leg2_side=Side.BUY,
        leg2_quantity=Decimal("0.5"),
        leg3_pair=_ETH_USDT,
        leg3_side=Side.SELL,
        leg3_quantity=Decimal("0.5"),
        expected_profit=Decimal("5"),
    )
    assert rm.check(signal) == RiskDecision.APPROVED


def test_risk_decision_is_strenum():
    # M-4: RiskDecision should now be a StrEnum, not a plain class with constants.
    assert RiskDecision.APPROVED.value == "approved"
    assert RiskDecision.REJECTED.value == "rejected"
    assert str(RiskDecision.APPROVED) == "approved"
