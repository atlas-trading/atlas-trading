"""
Pairs Trading Strategy (Statistical Arbitrage)

통계적 차익거래 전략
- 상관성 높은 두 자산의 가격 괴리를 이용
- Z-score 기반 평균회귀 전략
- 시장중립적 롱/숏 헷지
"""

from typing import List
import pandas as pd
import numpy as np
from app.strategies.base import (
    Strategy, Signal, DataRequirement, ParameterSchema
)


class PairsTradingStrategy(Strategy):
    """
    Pairs Trading Strategy (Statistical Arbitrage)

    두 자산 간의 스프레드가 평균에서 이탈할 때 평균회귀를 노리는 전략

    Parameters:
        pair_symbol: 페어 심볼 (예: "ETH/USDT", 기본값: "ETH/USDT")
        lookback_period: 스프레드 계산 기간 (기본값: 20)
        entry_zscore: 진입 Z-score 임계값 (기본값: 2.0)
        exit_zscore: 청산 Z-score 임계값 (기본값: 0.5)
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        pair_symbol: str = "ETH/USDT",
        lookback_period: int = 20,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            pair_symbol=pair_symbol,
            lookback_period=lookback_period,
            entry_zscore=entry_zscore,
            exit_zscore=exit_zscore,
            **kwargs
        )

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        페어 가격 및 스프레드 계산
        실제 운영 시에는 두 번째 자산 데이터를 별도로 가져와야 함
        """
        # 시뮬레이션: ETH는 BTC의 80%로 가정하고 노이즈 추가
        if 'pair_close' not in df.columns:
            # BTC 가격의 0.03배 정도로 ETH 시뮬레이션 (실제론 별도 데이터)
            df['pair_close'] = df['close'] * 0.03 * (1 + np.random.randn(len(df)) * 0.02)

        # 로그 가격비 (스프레드)
        df['log_ratio'] = np.log(df['close']) - np.log(df['pair_close'])

        # 스프레드의 이동평균 및 표준편차
        df['spread_mean'] = df['log_ratio'].rolling(window=self.lookback_period).mean()
        df['spread_std'] = df['log_ratio'].rolling(window=self.lookback_period).std()

        # Z-score 계산
        df['zscore'] = (df['log_ratio'] - df['spread_mean']) / df['spread_std']

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """
        Pairs Trading 시그널 생성

        - zscore > entry_zscore: A 과대평가 → A 숏, B 롱
        - zscore < -entry_zscore: A 저평가 → A 롱, B 숏
        - abs(zscore) < exit_zscore: 스프레드 정상화 → 청산
        """
        zscore = row.get('zscore')

        if pd.isna(zscore):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for spread calculation')

        # A(BTC) 과대평가 → A 숏
        if zscore > self.entry_zscore and not self.has_position:
            confidence = min(zscore / self.entry_zscore, 3.0) / 3.0
            return Signal(
                action='short',
                symbol=self.symbol,
                size=0.8,
                stop_loss=None,  # 페어 트레이딩은 헷지되어 있음
                take_profit=None,
                reason=f'Spread too wide: Z={zscore:.2f} (short {self.symbol}, long {self.pair_symbol})',
                confidence=confidence
            )

        # A(BTC) 저평가 → A 롱
        elif zscore < -self.entry_zscore and not self.has_position:
            confidence = min(abs(zscore) / self.entry_zscore, 3.0) / 3.0
            return Signal(
                action='long',
                symbol=self.symbol,
                size=0.8,
                stop_loss=None,
                take_profit=None,
                reason=f'Spread too narrow: Z={zscore:.2f} (long {self.symbol}, short {self.pair_symbol})',
                confidence=confidence
            )

        # 스프레드 정상화 → 청산
        elif self.has_position and abs(zscore) < self.exit_zscore:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'Spread normalized: Z={zscore:.2f}',
                confidence=1.0
            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """필요한 데이터 요구사항"""
        return [
            DataRequirement(
                symbol=self.symbol,
                timeframe='1h',
                lookback=self.lookback_period + 50
            ),
            DataRequirement(
                symbol=self.pair_symbol,
                timeframe='1h',
                lookback=self.lookback_period + 50
            )
        ]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """파라미터 스키마 정의"""
        return [
            {
                'name': 'pair_symbol',
                'type': 'string',
                'default': 'ETH/USDT',
                'description': 'Pair symbol to trade against',
                'required': True
            },
            {
                'name': 'lookback_period',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 100,
                'step': 5,
                'description': 'Lookback period for spread calculation',
                'required': True
            },
            {
                'name': 'entry_zscore',
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 4.0,
                'step': 0.5,
                'description': 'Entry Z-score threshold',
                'required': True
            },
            {
                'name': 'exit_zscore',
                'type': 'float',
                'default': 0.5,
                'min': 0.0,
                'max': 1.5,
                'step': 0.25,
                'description': 'Exit Z-score threshold',
                'required': True
            }
        ]
