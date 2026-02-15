"""
RSI Mean Reversion 전략

RSI(Relative Strength Index)를 이용한 평균회귀 전략
- RSI < 30 (과매도): 매수 진입
- RSI > 70 (과매수): 매도 청산
- 포지션 크기: 100% (풀 포지션)
"""

from typing import List
import pandas as pd
from app.strategies.base import (
    Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin
)


class RSIMeanReversionStrategy(Strategy, IndicatorMixin):
    """
    RSI 평균회귀 전략

    RSI 지표를 활용해 과매도/과매수 구간에서 평균 회귀를 노리는 전략

    Parameters:
        rsi_period: RSI 계산 기간 (기본값: 14)
        oversold_threshold: 과매도 임계값 (기본값: 30)
        overbought_threshold: 과매수 임계값 (기본값: 70)
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        rsi_period: int = 14,
        oversold_threshold: float = 30,
        overbought_threshold: float = 70,
        **kwargs
    ):
        super().__init__(symbol=symbol, rsi_period=rsi_period,
                        oversold_threshold=oversold_threshold,
                        overbought_threshold=overbought_threshold,
                        **kwargs)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI 지표 추가"""
        df = self.add_rsi(df, self.rsi_period)
        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """
        RSI 평균회귀 시그널 생성

        - RSI < oversold_threshold: long 진입
        - RSI > overbought_threshold: close 청산
        """
        rsi = row.get(f'rsi_{self.rsi_period}')

        # RSI 계산 안 됐으면 대기
        if pd.isna(rsi):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for RSI calculation')

        # 과매도 상태에서 매수 (포지션 없을 때만)
        if rsi < self.oversold_threshold and not self.has_position:
            # RSI가 낮을수록 신뢰도 높음
            confidence = 1.0 - (rsi / self.oversold_threshold)
            return Signal(
                action='long',
                symbol=self.symbol,
                size=0.8,  # 80% 포지션
                stop_loss=0.95,  # 5% 손절
                take_profit=None,  # RSI 기반 청산
                reason=f'RSI oversold: {rsi:.2f} < {self.oversold_threshold}',
                confidence=confidence
            )

        # 과매수 상태에서 청산 (포지션 있을 때만)
        elif rsi > self.overbought_threshold and self.has_position:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'RSI overbought: {rsi:.2f} > {self.overbought_threshold}',
                confidence=1.0
            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """필요한 데이터 요구사항"""
        return [
            DataRequirement(
                symbol=self.symbol,
                timeframe='1h',  # 1시간봉
                lookback=self.rsi_period + 50  # RSI 계산 + 여유분
            )
        ]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """파라미터 스키마 정의"""
        return [
            {
                'name': 'rsi_period',
                'type': 'int',
                'default': 14,
                'min': 5,
                'max': 50,
                'step': 1,
                'description': 'RSI calculation period',
                'required': True
            },
            {
                'name': 'oversold_threshold',
                'type': 'float',
                'default': 30,
                'min': 10,
                'max': 40,
                'step': 5,
                'description': 'RSI oversold threshold (buy signal)',
                'required': True
            },
            {
                'name': 'overbought_threshold',
                'type': 'float',
                'default': 70,
                'min': 60,
                'max': 90,
                'step': 5,
                'description': 'RSI overbought threshold (sell signal)',
                'required': True
            }
        ]
