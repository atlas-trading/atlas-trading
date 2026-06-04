from dataclasses import dataclass
from decimal import Decimal

from atlas.execution.order_status import OrderStatus


@dataclass(frozen=True, kw_only=True)
class OrderResult:
    id: str
    status: OrderStatus | None = None
    symbol: str | None = None
    type: str | None = None
    side: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    price: Decimal | None = None
    average: Decimal | None = None
    amount: Decimal | None = None
    filled: Decimal | None = None
    remaining: Decimal | None = None
    cost: Decimal | None = None
    client_order_id: str | None = None
    time_in_force: str | None = None
    post_only: bool | None = None
    reduce_only: bool | None = None
