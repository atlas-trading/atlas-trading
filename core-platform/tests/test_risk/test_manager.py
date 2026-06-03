from decimal import Decimal

from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.risk.manager import RiskDecision, RiskManager

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_USDT = TradingPair(ticker=Ticker.ETH, quote=Quote.USDT)


def _make_signal(qty: Decimal = Decimal("0.01")) -> ArbSignal:
    return ArbSignal(
        leg1_pair=_BTC_USDT,
        leg1_quantity=qty,
        leg2_pair=_ETH_USDT,
        leg2_quantity=qty,
        leg3_pair=_BTC_USDT,
        leg3_quantity=qty,
        expected_profit=Decimal("5"),
    )


def test_approved_within_limits():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    assert rm.check(_make_signal()) == RiskDecision.APPROVED


def test_rejected_kill_switch():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    rm.set_kill_switch(True)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_rejected_not_connected():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    rm.set_connected(False)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED


def test_rejected_order_size_exceeded():
    rm = RiskManager(max_order_size=Decimal("0.005"), max_exposure=Decimal("10"))
    assert rm.check(_make_signal(qty=Decimal("0.01"))) == RiskDecision.REJECTED


def test_rejected_exposure_exceeded():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("0.02"))
    assert rm.check(_make_signal(qty=Decimal("0.01"))) == RiskDecision.REJECTED


def test_kill_switch_toggle():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    rm.set_kill_switch(True)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED
    rm.set_kill_switch(False)
    assert rm.check(_make_signal()) == RiskDecision.APPROVED


def test_reconnect_resumes():
    rm = RiskManager(max_order_size=Decimal("1"), max_exposure=Decimal("10"))
    rm.set_connected(False)
    assert rm.check(_make_signal()) == RiskDecision.REJECTED
    rm.set_connected(True)
    assert rm.check(_make_signal()) == RiskDecision.APPROVED
