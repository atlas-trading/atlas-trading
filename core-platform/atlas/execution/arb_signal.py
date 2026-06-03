from dataclasses import dataclass
from decimal import Decimal

from atlas.core.trading_pair import TradingPair


@dataclass(frozen=True, kw_only=True)
class ArbSignal:
    leg1_pair: TradingPair
    leg1_quantity: Decimal
    leg2_pair: TradingPair
    leg2_quantity: Decimal
    leg3_pair: TradingPair
    leg3_quantity: Decimal
    expected_profit: Decimal
