from dataclasses import dataclass
from decimal import Decimal

from atlas.events.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class TradeResultEvent(BaseEvent):
    arb_id: str
    net_pnl: Decimal
    completed: bool  # False = UNWIND_COMPLETE
