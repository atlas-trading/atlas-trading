from atlas.core.asset import Asset
from atlas.core.trading_pair import TradingPair


def parse_trading_pair(symbol: str) -> TradingPair:
    base, quote = symbol.split("/")
    return TradingPair(base=Asset(base), quote=Asset(quote))
