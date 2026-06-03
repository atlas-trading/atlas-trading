from dataclasses import dataclass
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair


@dataclass(frozen=True, kw_only=True)
class OHLCV:
    exchange: Exchange
    trading_pair: TradingPair
    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
