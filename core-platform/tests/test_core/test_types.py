from atlas.core.parsers import parse_trading_pair
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker


def test_parse_trading_pair():
    pair = parse_trading_pair("BTC/USDT")
    assert pair.ticker is Ticker.BTC
    assert pair.quote is Quote.USDT
