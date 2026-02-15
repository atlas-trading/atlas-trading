"""
Funding Rate Arbitrage Strategy

펀딩비 차익거래 전략
- 선물 펀딩비가 임계값 이상: 선물 숏 + 현물 롱 (헷지)
- 선물 펀딩비가 임계값 이하: 선물 롱 + 현물 숏 (헷지)
- 시장중립적 전략으로 방향성 리스크 제거
"""

from typing import List
import pandas as pd
from app.strategies.base import (
    Strategy, Signal, DataRequirement, ParameterSchema
)


class FundingRateArbitrageStrategy(Strategy):
    """
    Funding Rate Arbitrage Strategy

    선물 펀딩비를 활용한 시장중립 차익거래 전략

    Parameters:
        funding_threshold: 진입 펀딩비 임계값 (%, 기본값: 0.05)
        exit_threshold: 청산 펀딩비 임계값 (%, 기본값: 0.01)
        hedge_ratio: 헷지 비율 (기본값: 1.0 = 100% 헷지)
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        funding_threshold: float = 0.05,
        exit_threshold: float = 0.01,
        hedge_ratio: float = 1.0,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            funding_threshold=funding_threshold,
            exit_threshold=exit_threshold,
            hedge_ratio=hedge_ratio,
            **kwargs
        )

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        펀딩비 데이터가 없으면 시뮬레이션
        실제 운영 시에는 거래소 API에서 가져와야 함
        """
        if 'funding_rate' not in df.columns:
            # 변동성 기반 펀딩비 시뮬레이션 (실제 데이터 대용)
            returns = df['close'].pct_change()
            volatility = returns.rolling(window=24).std()
            # 변동성 높을수록 펀딩비 증가 (불마켓 가정)
            df['funding_rate'] = (volatility * 100).clip(-0.3, 0.3)
            df['funding_rate'] = df['funding_rate'].fillna(0)

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """
        Funding Rate Arbitrage 시그널 생성

        - funding_rate > threshold: 선물 숏 포지션 (펀딩비 수취)
        - funding_rate < -threshold: 선물 롱 포지션 (펀딩비 수취)
        - abs(funding_rate) < exit_threshold: 포지션 청산
        """
        funding_rate = row.get('funding_rate', 0)

        # 펀딩비가 높으면 숏 (롱이 숏에게 지불)
        if funding_rate > self.funding_threshold and not self.has_position:
            confidence = min(funding_rate / self.funding_threshold, 2.0) / 2.0
            return Signal(
                action='short',
                symbol=self.symbol,
                size=self.hedge_ratio,
                stop_loss=None,  # 헷지되어 있어 손절 불필요
                take_profit=None,
                reason=f'High funding rate: {funding_rate:.4f}% (short perp + long spot)',
                confidence=confidence
            )

        # 펀딩비가 낮으면 롱 (숏이 롱에게 지불)
        elif funding_rate < -self.funding_threshold and not self.has_position:
            confidence = min(abs(funding_rate) / self.funding_threshold, 2.0) / 2.0
            return Signal(
                action='long',
                symbol=self.symbol,
                size=self.hedge_ratio,
                stop_loss=None,
                take_profit=None,
                reason=f'Negative funding rate: {funding_rate:.4f}% (long perp + short spot)',
                confidence=confidence
            )

        # 펀딩비가 정상화되면 청산
        elif self.has_position and abs(funding_rate) < self.exit_threshold:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason=f'Funding rate normalized: {funding_rate:.4f}%',
                confidence=1.0
            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """필요한 데이터 요구사항"""
        return [
            DataRequirement(
                symbol=self.symbol,
                timeframe='1h',  # 펀딩비는 8시간마다지만 1시간봉으로 모니터링
                lookback=100
            )
        ]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """파라미터 스키마 정의"""
        return [
            {
                'name': 'funding_threshold',
                'type': 'float',
                'default': 0.05,
                'min': 0.01,
                'max': 0.5,
                'step': 0.01,
                'description': 'Entry funding rate threshold (%)',
                'required': True
            },
            {
                'name': 'exit_threshold',
                'type': 'float',
                'default': 0.01,
                'min': 0.0,
                'max': 0.1,
                'step': 0.01,
                'description': 'Exit funding rate threshold (%)',
                'required': True
            },
            {
                'name': 'hedge_ratio',
                'type': 'float',
                'default': 1.0,
                'min': 0.5,
                'max': 1.0,
                'step': 0.1,
                'description': 'Hedge ratio (1.0 = 100% hedge)',
                'required': True
            }
        ]
