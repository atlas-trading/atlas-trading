from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair
from atlas.execution.order_status import OrderStatus
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side


@dataclass
class Order:
    id: str
    exchange: Exchange
    trading_pair: TradingPair
    side: Side
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None  # None for MARKET orders
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
