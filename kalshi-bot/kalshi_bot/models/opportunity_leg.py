from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, kw_only=True)
class OpportunityLeg:
    ticker: str
    side: Literal["yes", "no"]
    price: Decimal
    available_size: Decimal
