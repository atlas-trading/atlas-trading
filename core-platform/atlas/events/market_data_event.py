from dataclasses import dataclass
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair
from atlas.events.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class MarketDataEvent(BaseEvent):
    exchange: Exchange
    trading_pair: TradingPair
    bid: Decimal
    ask: Decimal
    last: Decimal
