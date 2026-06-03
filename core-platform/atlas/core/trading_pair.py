from dataclasses import dataclass


@dataclass(frozen=True)
class TradingPair:
    base: str
    quote: str
