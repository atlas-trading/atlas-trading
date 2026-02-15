"""
RSI 전략

과매도/과매수 구간에서 역추세 매매를 하는 전략
"""

import pandas as pd
from app.strategies.base import Strategy, IndicatorMixin, SignalType


class RSIStrategy(Strategy, IndicatorMixin):
    """
    RSI 전략

    Parameters:
        rsi_period: RSI 계산 기간 (기본값: 14)
        oversold_level: 과매도 기준선 (기본값: 30)
        overbought_level: 과매수 기준선 (기본값: 70)
        hold_bars: 최소 보유 기간 (캔들 수, 기본값: 5)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_level: float = 30,
        overbought_level: float = 70,
        hold_bars: int = 5
    ):
        super().__init__()
        self.rsi_period = rsi_period
        self.oversold_level = oversold_level
        self.overbought_level = overbought_level
        self.hold_bars = hold_bars

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI 지표 추가"""
        df = self.add_rsi(df, period=self.rsi_period)
        return df

    def on_bar(self, row: pd.Series) -> SignalType:
        """
        RSI 시그널 생성

        - RSI < oversold_level: long 진입 (과매도)
        - RSI > overbought_level OR 최소 보유 기간 충족: close 청산
        """
        rsi = row.get('rsi')

        # RSI 계산 안 됐으면 대기
        if pd.isna(rsi):
            return None

        signal = None

        # 과매도 구간에서 롱 진입
        if rsi < self.oversold_level and not self.has_position:
            signal = 'long'

        # 과매수 구간이거나 최소 보유 기간 충족 시 청산
        elif self.has_position:
            if rsi > self.overbought_level or self.bars_since_entry >= self.hold_bars:
                signal = 'close'

        return signal
