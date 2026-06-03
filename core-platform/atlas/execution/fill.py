from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from atlas.core.time import utc_now
from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side


@dataclass(frozen=True, kw_only=True)
class Fill:
    order_id: str
    arb_id: str
    leg: int
    trading_pair: TradingPair
    side: Side
    filled_qty: Decimal
    filled_price: Decimal
    fee: Decimal
    filled_at: datetime = field(default_factory=utc_now)
