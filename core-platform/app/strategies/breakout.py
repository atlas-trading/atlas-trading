"""
Breakout Strategy

돌파 전략
- Donchian Channel을 이용한 가격 돌파 전략
- ATR 기반 손절/익절 설정
- 변동성 필터링으로 거짓 돌파 방지
"""

from typing import List
import pandas as pd
from app.strategies.base import (
    Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin
)


class BreakoutStrategy(Strategy, IndicatorMixin):
    """
    Breakout Strategy

    Donchian Channel 돌파를 이용한 모멘텀 전략

    Parameters:
        breakout_period: Donchian Channel 기간 (기본값: 20)
        atr_period: ATR 계산 기간 (기본값: 14)
        atr_multiplier: ATR 배수 (손절/익절, 기본값: 2.0)
        volatility_filter: 변동성 필터 사용 여부 (기본값: True)
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        breakout_period: int = 20,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        volatility_filter: bool = True,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            breakout_period=breakout_period,
            atr_period=atr_period,
            atr_multiplier=atr_multiplier,
            volatility_filter=volatility_filter,
            **kwargs
        )

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Donchian Channel 및 ATR 지표 추가"""
        df = self.add_donchian_channel(df, self.breakout_period)
        df = self.add_atr(df, self.atr_period)

        # 변동성 필터 (ATR의 20일 이동평균)
        if self.volatility_filter:
            df['atr_ma'] = df[f'atr_{self.atr_period}'].rolling(window=20).mean()

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """
        Breakout 시그널 생성

        - 가격 > 최고가: 롱 진입
        - 가격 < 최저가: 청산 (또는 반대 포지션)
        """
        close = row['close']
        high = row['high']
        low = row['low']

        donchian_high = row.get(f'donchian_high_{self.breakout_period}')
        donchian_low = row.get(f'donchian_low_{self.breakout_period}')
        atr = row.get(f'atr_{self.atr_period}')

        # 지표 계산 대기
        if pd.isna(donchian_high) or pd.isna(atr):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicator calculation')

        # 변동성 필터 체크
        if self.volatility_filter:
            atr_ma = row.get('atr_ma')
            if pd.isna(atr_ma) or atr < atr_ma * 0.8:
                # 변동성이 너무 낮으면 거래 안 함 (거짓 돌파 가능성)
                if not self.has_position:
                    return Signal(action='hold', symbol=self.symbol, reason='Low volatility')

        # 상단 돌파 → 롱 진입
        if high > donchian_high and not self.has_position:
            # ATR 기반 손절/익절 설정
            stop_loss_price = close - (atr * self.atr_multiplier)
            take_profit_price = close + (atr * self.atr_multiplier * 2)  # 2:1 손익비

            stop_loss_pct = stop_loss_price / close
            take_profit_pct = take_profit_price / close

            confidence = min((high - donchian_high) / atr, 1.5) / 1.5

            return Signal(
                action='long',
                symbol=self.symbol,
                size=0.85,  # 85% 포지션
                stop_loss=stop_loss_pct,
                take_profit=take_profit_pct,
                reason=f'Upside breakout: {high:.2f} > {donchian_high:.2f}',
                confidence=confidence
            )

        # 하단 돌파 → 청산 (숏은 안전을 위해 구현 안 함)
        elif low < donchian_low and self.has_position:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'Downside breakout: {low:.2f} < {donchian_low:.2f}',
                confidence=1.0
            )

        # 채널 중간 이하로 하락 → 청산
        elif self.has_position:
            donchian_mid = row.get(f'donchian_mid_{self.breakout_period}')
            if not pd.isna(donchian_mid) and close < donchian_mid:
                return Signal(
                    action='close',
                    symbol=self.symbol,
                    reason='Price below channel mid',
                    confidence=0.8
                )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """필요한 데이터 요구사항"""
        return [
            DataRequirement(
                symbol=self.symbol,
                timeframe='1d',  # 일봉으로 중장기 돌파 포착
                lookback=max(self.breakout_period, self.atr_period) + 50
            )
        ]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """파라미터 스키마 정의"""
        return [
            {
                'name': 'breakout_period',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'step': 5,
                'description': 'Donchian Channel period',
                'required': True
            },
            {
                'name': 'atr_period',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'step': 1,
                'description': 'ATR calculation period',
                'required': True
            },
            {
                'name': 'atr_multiplier',
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 4.0,
                'step': 0.5,
                'description': 'ATR multiplier for stop loss/take profit',
                'required': True
            },
            {
                'name': 'volatility_filter',
                'type': 'bool',
                'default': True,
                'description': 'Use volatility filter to avoid false breakouts',
                'required': False
            }
        ]
