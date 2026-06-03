from dataclasses import dataclass
from decimal import Decimal

from atlas.events.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class SignalEvent(BaseEvent):
    strategy_id: str
    path: tuple[str, ...]  # ("BTC/USDT", "ETH/BTC", "ETH/USDT")
    expected_profit_pct: Decimal
