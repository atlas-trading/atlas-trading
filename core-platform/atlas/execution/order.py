from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.time import utc_now
from atlas.core.trading_pair import TradingPair
from atlas.execution.order_status import OrderStatus
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side


@dataclass(frozen=True, kw_only=True)
class Order:
    id: str
    exchange: Exchange
    trading_pair: TradingPair
    side: Side
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None  # None for MARKET orders
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
