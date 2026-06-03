from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.trading_pair import TradingPair


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class BaseEvent:
    timestamp: datetime = field(default_factory=_now)


@dataclass(frozen=True, kw_only=True)
class MarketDataEvent(BaseEvent):
    exchange: Exchange
    trading_pair: TradingPair
    bid: Decimal
    ask: Decimal
    last: Decimal


@dataclass(frozen=True, kw_only=True)
class SignalEvent(BaseEvent):
    strategy_id: str
    path: tuple[str, ...]  # ("BTC/USDT", "ETH/BTC", "ETH/USDT")
    expected_profit_pct: Decimal


@dataclass(frozen=True, kw_only=True)
class FillEvent(BaseEvent):
    arb_id: str
    leg: int
    trading_pair: TradingPair
    filled_qty: Decimal
    filled_price: Decimal


@dataclass(frozen=True, kw_only=True)
class TradeResultEvent(BaseEvent):
    arb_id: str
    net_pnl: Decimal
    completed: bool  # False = UNWIND_COMPLETE
