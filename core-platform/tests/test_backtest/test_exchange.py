from decimal import Decimal

import pytest

from atlas.backtest.exchange import BacktestExchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)

_TICKERS = {
    "BTC/USDT": {"bid": 50000.0, "ask": 50010.0, "last": 50005.0},
    "ETH/BTC": {"bid": 0.0666, "ask": 0.0668, "last": 0.0667},
}


def _order(pair: TradingPair, side: Side, qty: str = "0.01") -> Order:
    return Order(
        id="test-order",
        exchange=None,  # type: ignore[arg-type]
        trading_pair=pair,
        side=side,
        order_type=OrderType.MARKET,
        quantity=Decimal(qty),
    )


async def test_buy_fills_at_ask_plus_slippage():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")}, slippage=Decimal("0.001"))
    ex.update_prices(_TICKERS)
    result = await ex.place_order(_order(_BTC_USDT, Side.BUY))
    expected_price = Decimal("50010") * Decimal("1.001")
    assert result.status == OrderStatus.FILLED
    assert result.average == expected_price


async def test_sell_fills_at_bid_minus_slippage():
    ex = BacktestExchange(
        initial_balance={"USDT": Decimal("0"), "BTC": Decimal("1")}, slippage=Decimal("0.001")
    )
    ex.update_prices(_TICKERS)
    result = await ex.place_order(_order(_BTC_USDT, Side.SELL))
    expected_price = Decimal("50000") * Decimal("0.999")
    assert result.average == expected_price


async def test_buy_deducts_quote_adds_base():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")})
    ex.update_prices(_TICKERS)
    await ex.place_order(_order(_BTC_USDT, Side.BUY, "0.01"))
    assert ex.get_balance_for("USDT") < Decimal("1000")
    assert ex.get_balance_for("BTC") == Decimal("0.01")


async def test_sell_deducts_base_adds_quote():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("0"), "BTC": Decimal("0.01")})
    ex.update_prices(_TICKERS)
    await ex.place_order(_order(_BTC_USDT, Side.SELL, "0.01"))
    assert ex.get_balance_for("BTC") == Decimal("0")
    assert ex.get_balance_for("USDT") > Decimal("0")


async def test_insufficient_quote_raises():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1")})
    ex.update_prices(_TICKERS)
    with pytest.raises(RuntimeError, match="Insufficient"):
        await ex.place_order(_order(_BTC_USDT, Side.BUY, "1"))


async def test_no_price_raises():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")})
    with pytest.raises(RuntimeError, match="No price"):
        await ex.place_order(_order(_BTC_USDT, Side.BUY))


async def test_health_check_always_true():
    ex = BacktestExchange(initial_balance={})
    assert await ex.health_check() is True


async def test_update_prices_ignores_unknown_symbols():
    ex = BacktestExchange(initial_balance={})
    ex.update_prices({"INVALID_SYM": {"bid": 1, "ask": 2}})  # should not raise
