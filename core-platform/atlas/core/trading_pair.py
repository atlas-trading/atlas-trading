from dataclasses import dataclass
from atlas.core.ticker import Ticker
from atlas.core.quote import Quote


@dataclass(frozen=True)
class TradingPair:
    ticker: Ticker  # Ticker.BTC
    quote: Quote    # Quote.USDT
