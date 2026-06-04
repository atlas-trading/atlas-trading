from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair


def parse_trading_pair(symbol: str) -> TradingPair:
    # ccxt encodes futures symbols as "BASE/QUOTE:SETTLE" (e.g. "BTC/USDT:USDT").
    # We only support spot markets — reject anything that looks like a future.
    if ":" in symbol:
        raise ValueError(f"Futures symbols not supported: {symbol}")
    ticker, quote = symbol.split("/")
    return TradingPair(ticker=Ticker(ticker), quote=Quote(quote))


def to_ccxt_symbol(pair: TradingPair) -> str:
    return f"{pair.ticker}/{pair.quote}"
