from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class Candle:
    end_ts: int
    yes_bid_close: Decimal
    yes_bid_low: Decimal
    yes_ask_close: Decimal
    yes_ask_high: Decimal
