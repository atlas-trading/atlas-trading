"""
Trend Following Strategy

추세추종 전략
- 이동평균 크로스오버로 추세 파악
- ADX로 추세 강도 필터링
- 강한 추세에서만 진입
"""

from typing import List
import pandas as pd
from app.strategies.base import (
    Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin
)


class TrendFollowingStrategy(Strategy, IndicatorMixin):
    """
    Trend Following Strategy

    이동평균 크로스오버와 ADX를 활용한 추세추종 전략

    Parameters:
        fast_period: 단기 이동평균 기간 (기본값: 10)
        slow_period: 장기 이동평균 기간 (기본값: 30)
        adx_period: ADX 계산 기간 (기본값: 14)
        adx_threshold: ADX 임계값 (기본값: 25)
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        fast_period: int = 10,
        slow_period: int = 30,
        adx_period: int = 14,
        adx_threshold: float = 25,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            fast_period=fast_period,
            slow_period=slow_period,
            adx_period=adx_period,
            adx_threshold=adx_threshold,
            **kwargs
        )

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 및 ADX 지표 추가"""
        df = self.add_sma(df, self.fast_period)
        df = self.add_sma(df, self.slow_period)
        df = self.add_adx(df, self.adx_period)

        # 크로스오버 감지
        df['ma_diff'] = df[f'sma_{self.fast_period}'] - df[f'sma_{self.slow_period}']
        df['ma_diff_prev'] = df['ma_diff'].shift(1)

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """
        Trend Following 시그널 생성

        - 골든크로스 + ADX > threshold: 롱 진입
        - 데드크로스: 청산
        """
        sma_fast = row.get(f'sma_{self.fast_period}')
        sma_slow = row.get(f'sma_{self.slow_period}')
        adx = row.get(f'adx_{self.adx_period}')
        ma_diff = row.get('ma_diff')
        ma_diff_prev = row.get('ma_diff_prev')

        # 지표 계산 대기
        if pd.isna(sma_fast) or pd.isna(sma_slow) or pd.isna(adx):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicator calculation')

        # 골든크로스 (단기 > 장기) + 강한 추세
        if (ma_diff > 0 and ma_diff_prev <= 0 and
            adx > self.adx_threshold and not self.has_position):

            # ADX가 높을수록 신뢰도 높음
            confidence = min(adx / 50, 1.0)

            return Signal(
                action='long',
                symbol=self.symbol,
                size=0.9,  # 90% 포지션
                stop_loss=0.97,  # 3% 손절
                take_profit=None,  # 추세 끝날 때까지 보유
                reason=f'Golden cross + Strong trend (ADX={adx:.1f})',
                confidence=confidence
            )

        # 데드크로스 (단기 < 장기) → 청산
        elif ma_diff < 0 and ma_diff_prev >= 0 and self.has_position:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'Death cross (ADX={adx:.1f})',
                confidence=1.0
            )

        # ADX 약화 → 청산
        elif self.has_position and adx < self.adx_threshold * 0.7:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'Trend weakening (ADX={adx:.1f})',
                confidence=1.0
            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """필요한 데이터 요구사항"""
        return [
            DataRequirement(
                symbol=self.symbol,
                timeframe='4h',  # 4시간봉으로 중기 추세 포착
                lookback=max(self.slow_period, self.adx_period) + 50
            )
        ]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """파라미터 스키마 정의"""
        return [
            {
                'name': 'fast_period',
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 30,
                'step': 5,
                'description': 'Fast moving average period',
                'required': True
            },
            {
                'name': 'slow_period',
                'type': 'int',
                'default': 30,
                'min': 20,
                'max': 100,
                'step': 10,
                'description': 'Slow moving average period',
                'required': True
            },
            {
                'name': 'adx_period',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'step': 1,
                'description': 'ADX calculation period',
                'required': True
            },
            {
                'name': 'adx_threshold',
                'type': 'float',
                'default': 25,
                'min': 15,
                'max': 40,
                'step': 5,
                'description': 'ADX threshold for strong trend',
                'required': True
            }
        ]
