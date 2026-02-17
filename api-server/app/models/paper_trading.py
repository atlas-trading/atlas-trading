"""
Paper Trading 데이터 모델
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base


class SessionStatus(str, enum.Enum):
    """세션 상태"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PaperTradingSession(Base):
    """Paper Trading 세션"""
    __tablename__ = "paper_trading_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # 기본 정보
    name = Column(String, nullable=True)  # 사용자 지정 이름
    symbol = Column(String, nullable=False, index=True)  # BTC/USDT
    strategy = Column(String, nullable=False)  # Statistical Arbitrage

    # 자금
    initial_capital = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    current_equity = Column(Float, nullable=False)

    # 상태
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, index=True)

    # 시간
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 설정 (JSON)
    settings = Column(JSON, nullable=True)  # 리스크 한도, 기타 설정

    # 통계 (빠른 조회용)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    max_equity = Column(Float, nullable=True)
    max_drawdown = Column(Float, default=0.0)

    # Relationships
    trades = relationship("PaperTradingTrade", back_populates="session", cascade="all, delete-orphan")
    snapshots = relationship("PaperTradingSnapshot", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PaperTradingSession(id={self.id}, symbol={self.symbol}, status={self.status})>"


class PaperTradingTrade(Base):
    """Paper Trading 거래 기록"""
    __tablename__ = "paper_trading_trades"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("paper_trading_sessions.id"), nullable=False, index=True)

    # 거래 정보
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # buy, sell
    position_side = Column(String, nullable=False)  # open, close

    # 가격 및 수량
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)  # 진입 시에만
    exit_price = Column(Float, nullable=True)   # 청산 시에만

    # 비용
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)

    # 손익 (청산 시에만)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)

    # 포지션 정보
    position_type = Column(String, nullable=True)  # long, short
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    exit_reason = Column(String, nullable=True)  # signal, stop_loss, take_profit

    # 시간
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    session = relationship("PaperTradingSession", back_populates="trades")

    def __repr__(self):
        return f"<PaperTradingTrade(id={self.id}, side={self.side}, pnl={self.pnl})>"


class PaperTradingSnapshot(Base):
    """Paper Trading 상태 스냅샷 (10초마다 저장)"""
    __tablename__ = "paper_trading_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("paper_trading_sessions.id"), nullable=False, index=True)

    # 계좌 상태
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)

    # 포지션 (JSON)
    open_positions = Column(JSON, nullable=True)  # [{symbol, side, quantity, entry_price, ...}]

    # 시장 데이터
    market_price = Column(Float, nullable=True)

    # 시간
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    session = relationship("PaperTradingSession", back_populates="snapshots")

    def __repr__(self):
        return f"<PaperTradingSnapshot(id={self.id}, equity={self.equity})>"
