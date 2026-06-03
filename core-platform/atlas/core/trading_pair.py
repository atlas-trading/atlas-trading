from dataclasses import dataclass
from atlas.core.asset import Asset


@dataclass(frozen=True)
class TradingPair:
    base: Asset   # Asset.BTC
    quote: Asset  # Asset.USDT
