from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair


def parse_trading_pair(symbol: str) -> TradingPair:
    ticker, quote = symbol.split("/")
    return TradingPair(ticker=Ticker(ticker), quote=Quote(quote))
