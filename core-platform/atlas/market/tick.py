from dataclasses import dataclass
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair


@dataclass(frozen=True, kw_only=True)
class Tick:
    exchange: Exchange
    trading_pair: TradingPair
    timestamp: int
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
