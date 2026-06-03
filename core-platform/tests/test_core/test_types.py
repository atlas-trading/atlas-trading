from atlas.core.parsers import parse_trading_pair, to_ccxt_symbol
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker


def test_parse_trading_pair():
    pair = parse_trading_pair("BTC/USDT")
    assert pair.ticker is Ticker.BTC
    assert pair.quote is Quote.USDT


def test_to_ccxt_symbol():
    pair = parse_trading_pair("BTC/USDT")
    assert to_ccxt_symbol(pair) == "BTC/USDT"
