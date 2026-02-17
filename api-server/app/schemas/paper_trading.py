"""
Paper Trading Pydantic 스키마
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class PaperTradingSessionCreate(BaseModel):
    name: Optional[str] = None
    symbol: str = Field(..., example="BTC/USDT")
    strategy: str = Field(..., example="Statistical Arbitrage")
    initial_capital: float = Field(..., gt=0, example=10000.0)
    settings: Optional[Dict[str, Any]] = None


class PaperTradingSessionUpdate(BaseModel):
    status: Optional[str] = None
    current_balance: Optional[float] = None
    current_equity: Optional[float] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    total_pnl: Optional[float] = None
    total_commission: Optional[float] = None
    max_equity: Optional[float] = None
    max_drawdown: Optional[float] = None


class PaperTradingSessionResponse(BaseModel):
    id: int
    name: Optional[str]
    symbol: str
    strategy: str
    initial_capital: float
    current_balance: float
    current_equity: float
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    last_update: datetime
    settings: Optional[Dict[str, Any]]
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    total_commission: float
    max_equity: Optional[float]
    max_drawdown: float

    class Config:
        orm_mode = True


class PaperTradingTradeResponse(BaseModel):
    id: int
    session_id: int
    symbol: str
    side: str
    position_side: str
    quantity: float
    entry_price: Optional[float]
    exit_price: Optional[float]
    commission: float
    slippage: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    position_type: Optional[str]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    exit_reason: Optional[str]
    timestamp: datetime

    class Config:
        orm_mode = True


class PaperTradingSnapshotResponse(BaseModel):
    id: int
    session_id: int
    balance: float
    equity: float
    unrealized_pnl: float
    open_positions: Optional[List[Dict[str, Any]]]
    market_price: Optional[float]
    timestamp: datetime

    class Config:
        orm_mode = True


class PaperTradingStats(BaseModel):
    session_id: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_commission: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]


class KlineData(BaseModel):
    time: int = Field(..., description="Unix timestamp in milliseconds")
    open: float
    high: float
    low: float
    close: float
    volume: float
