from dataclasses import dataclass

from atlas.core.quote import Quote
from atlas.core.ticker import Ticker


@dataclass(frozen=True)
class TradingPair:
    ticker: Ticker  # Ticker.BTC
    quote: Quote  # Quote.USDT
