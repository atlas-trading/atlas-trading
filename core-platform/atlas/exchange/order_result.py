from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class OrderResult:
    id: str
    status: str | None = None
    symbol: str | None = None
    type: str | None = None
    side: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    price: float | None = None
    average: float | None = None
    amount: float | None = None
    filled: float | None = None
    remaining: float | None = None
    cost: float | None = None
    client_order_id: str | None = None
    time_in_force: str | None = None
    post_only: bool | None = None
    reduce_only: bool | None = None
