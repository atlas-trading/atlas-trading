from dataclasses import dataclass
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side


@dataclass(frozen=True, kw_only=True)
class ArbSignal:
    exchange: Exchange
    leg1_pair: TradingPair
    leg1_side: Side
    leg1_quantity: Decimal
    leg2_pair: TradingPair
    leg2_side: Side
    leg2_quantity: Decimal
    leg3_pair: TradingPair
    leg3_side: Side
    leg3_quantity: Decimal
    expected_profit: Decimal
