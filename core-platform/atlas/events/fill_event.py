from dataclasses import dataclass
from decimal import Decimal

from atlas.core.trading_pair import TradingPair
from atlas.events.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class FillEvent(BaseEvent):
    arb_id: str
    leg: int
    trading_pair: TradingPair
    filled_qty: Decimal
    filled_price: Decimal
