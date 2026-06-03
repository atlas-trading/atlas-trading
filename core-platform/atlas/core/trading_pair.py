from dataclasses import dataclass


@dataclass(frozen=True)
class TradingPair:
    base: str   # "BTC"
    quote: str  # "USDT"
