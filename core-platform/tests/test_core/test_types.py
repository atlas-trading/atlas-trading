from decimal import Decimal
from atlas.core.ticker import Ticker
from atlas.core.quote import Quote
from atlas.core.parsers import parse_trading_pair


def test_parse_trading_pair():
    pair = parse_trading_pair("BTC/USDT")
    assert pair.ticker is Ticker.BTC
    assert pair.quote is Quote.USDT


def test_amount_decimal_precision():
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    assert 0.1 + 0.2 != 0.3
