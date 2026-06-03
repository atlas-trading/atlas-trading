from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class Balance:
    usdt: Decimal
    btc: Decimal
    eth: Decimal
