from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class OrderResult:
    order_id: str
    client_order_id: str
    fill_count: Decimal
    remaining_count: Decimal
    average_fill_price: Decimal | None
    average_fee_paid: Decimal | None
