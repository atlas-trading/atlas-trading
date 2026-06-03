from dataclasses import dataclass
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair


@dataclass(frozen=True, kw_only=True)
class OrderBook:
    exchange: Exchange
    trading_pair: TradingPair
    timestamp: int
    bids: tuple[tuple[Decimal, Decimal], ...]
    asks: tuple[tuple[Decimal, Decimal], ...]
