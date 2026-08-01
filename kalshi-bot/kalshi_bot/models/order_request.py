from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, kw_only=True)
class OrderRequest:
    ticker: str
    side: Literal["bid", "ask"]
    price: Decimal
    count: Decimal
    time_in_force: Literal["immediate_or_cancel", "fill_or_kill", "good_till_canceled"]
    client_order_id: str
