"""Strategy configuration models"""
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.models.base import Base


class StrategyConfig(Base):
    """
    전략 설정 저장 테이블

    어드민에서 전략별 파라미터를 저장하고 관리
    """
    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True, index=True)

    # 전략 정보
    strategy_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)  # 화면 표시용 이름
    description = Column(Text, nullable=True)

    # 파라미터 (JSON)
    parameters = Column(JSON, nullable=False, default={})

    # 상태
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # 활성화 여부
    is_live = Column(Boolean, default=False, nullable=False)  # 실거래 여부

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 백테스트 통계 (캐시용)
    last_backtest_id = Column(Integer, nullable=True)
    last_backtest_return = Column(Integer, nullable=True)  # 최근 백테스트 수익률 (%)
    last_backtest_sharpe = Column(Integer, nullable=True)  # 최근 백테스트 샤프 비율
    last_backtest_date = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StrategyConfig(name={self.strategy_name}, active={self.is_active})>"

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'display_name': self.display_name,
            'description': self.description,
            'parameters': self.parameters,
            'is_active': self.is_active,
            'is_live': self.is_live,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_backtest_id': self.last_backtest_id,
            'last_backtest_return': self.last_backtest_return,
            'last_backtest_sharpe': self.last_backtest_sharpe,
            'last_backtest_date': self.last_backtest_date.isoformat() if self.last_backtest_date else None,
        }
