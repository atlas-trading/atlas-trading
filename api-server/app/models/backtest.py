"""Backtest result models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BacktestRun(Base):
    """백테스트 실행 정보"""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(100), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Initial settings
    initial_capital = Column(Float, nullable=False)
    commission = Column(Float, nullable=False)

    # Results
    final_capital = Column(Float)
    total_return = Column(Float)  # 총 수익률 (%)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)  # 승률 (%)
    max_drawdown = Column(Float)  # 최대 낙폭 (%)
    sharpe_ratio = Column(Float)  # 샤프 비율

    # Parameters (JSON string)
    parameters = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    trades = relationship("BacktestTrade", back_populates="backtest_run", cascade="all, delete-orphan")
    equity_curve = relationship("BacktestEquity", back_populates="backtest_run", cascade="all, delete-orphan")


class BacktestTrade(Base):
    """백테스트 거래 기록"""
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)

    # Trade info
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    side = Column(String(10), nullable=False)  # 'long' or 'short'
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Float, nullable=False)

    # Results
    pnl = Column(Float)  # 손익
    pnl_pct = Column(Float)  # 손익률 (%)
    commission_paid = Column(Float)  # 수수료
    position_size_pct = Column(Float, default=1.0)  # 포지션 크기 (자본 대비 비율)

    # Relationship
    backtest_run = relationship("BacktestRun", back_populates="trades")


class BacktestEquity(Base):
    """백테스트 자산 곡선"""
    __tablename__ = "backtest_equity"

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, index=True)
    equity = Column(Float, nullable=False)  # 총 자산
    cash = Column(Float, nullable=False)  # 현금
    position_value = Column(Float, nullable=False)  # 포지션 가치

    # Relationship
    backtest_run = relationship("BacktestRun", back_populates="equity_curve")
