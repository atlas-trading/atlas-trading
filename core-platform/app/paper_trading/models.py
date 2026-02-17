"""Data models for Paper Trading system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4


@dataclass
class Order:
    """Order information."""

    id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    side: Literal["buy", "sell"] = "buy"
    type: Literal["market", "limit"] = "market"
    quantity: float = 0.0
    price: Optional[float] = None  # for limit orders
    status: Literal["pending", "filled", "cancelled"] = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class Position:
    """Position information."""

    symbol: str
    side: Literal["long", "short"]
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    commission_paid: float = 0.0


@dataclass
class Trade:
    """Executed trade record."""

    id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    side: Literal["buy", "sell"] = "buy"
    quantity: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    pnl: Optional[float] = None  # only for closing trades
