"""
골든 크로스 전략

단기 이동평균이 장기 이동평균을 상향 돌파하면 매수,
하향 돌파하면 매도하는 전통적인 추세 추종 전략
"""

import pandas as pd
from app.strategies.base import Strategy, IndicatorMixin, SignalType


class GoldenCrossStrategy(Strategy, IndicatorMixin):
    """
    골든 크로스 전략

    Parameters:
        fast_period: 단기 이동평균 기간 (기본값: 50)
        slow_period: 장기 이동평균 기간 (기본값: 200)
        ma_type: 이동평균 타입 ('sma' or 'ema', 기본값: 'sma')
    """

    def __init__(
        self,
        fast_period: int = 50,
        slow_period: int = 200,
        ma_type: str = 'sma'
    ):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type

        # 이전 값 저장 (크로스 감지용)
        self.prev_fast_ma = None
        self.prev_slow_ma = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 지표 추가"""
        if self.ma_type == 'sma':
            df = self.add_sma(df, self.fast_period)
            df = self.add_sma(df, self.slow_period)
        else:  # ema
            df = self.add_ema(df, self.fast_period)
            df = self.add_ema(df, self.slow_period)

        return df

    def on_bar(self, row: pd.Series) -> SignalType:
        """
        골든 크로스 시그널 생성

        - 골든 크로스 (fast > slow): long 진입
        - 데드 크로스 (fast < slow): close 청산
        """
        fast_ma = row.get(f'{self.ma_type}_{self.fast_period}')
        slow_ma = row.get(f'{self.ma_type}_{self.slow_period}')

        # 지표 계산 안 됐으면 대기
        if pd.isna(fast_ma) or pd.isna(slow_ma):
            self.prev_fast_ma = fast_ma
            self.prev_slow_ma = slow_ma
            return None

        signal = None

        # 크로스 감지 (이전 값이 있을 때만)
        if self.prev_fast_ma is not None and self.prev_slow_ma is not None:
            # 골든 크로스: fast가 slow를 상향 돌파
            if (self.prev_fast_ma <= self.prev_slow_ma) and (fast_ma > slow_ma):
                if not self.has_position:
                    signal = 'long'

            # 데드 크로스: fast가 slow를 하향 돌파
            elif (self.prev_fast_ma >= self.prev_slow_ma) and (fast_ma < slow_ma):
                if self.has_position:
                    signal = 'close'

        # 이전 값 업데이트
        self.prev_fast_ma = fast_ma
        self.prev_slow_ma = slow_ma

        return signal

    def reset(self) -> None:
        """전략 상태 초기화"""
        super().reset()
        self.prev_fast_ma = None
        self.prev_slow_ma = None
