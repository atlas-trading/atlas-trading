"""Golden Cross Strategy

골든 크로스 전략:
- MA 50이 MA 200을 상향 돌파하면 매수 (long)
- MA 50이 MA 200을 하향 돌파하면 매도 (close)
"""
import pandas as pd
from typing import Optional, Dict, Any


class GoldenCrossStrategy:
    """골든 크로스 전략"""

    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        """
        Args:
            fast_period: 빠른 이동평균 기간 (default: 50)
            slow_period: 느린 이동평균 기간 (default: 200)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"GoldenCross_{fast_period}_{slow_period}"

        # 이전 캔들의 크로스 상태 추적
        self.prev_fast_ma = None
        self.prev_slow_ma = None
        self.position_open = False

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
        }

    def generate_signal(self, row: pd.Series) -> Optional[str]:
        """
        각 캔들에 대해 거래 시그널 생성

        Args:
            row: OHLCV 데이터 행 (timestamp, open, high, low, close, volume, sma_50, sma_200 포함)

        Returns:
            'long': 롱 포지션 진입
            'close': 포지션 청산
            None: 아무 행동도 하지 않음
        """
        # 이동평균선 값
        fast_ma = row.get(f"sma_{self.fast_period}")
        slow_ma = row.get(f"sma_{self.slow_period}")

        # 이동평균선이 아직 계산되지 않은 경우 (초기 기간)
        if pd.isna(fast_ma) or pd.isna(slow_ma):
            return None

        signal = None

        # 이전 값이 있는 경우에만 크로스 감지
        if self.prev_fast_ma is not None and self.prev_slow_ma is not None:
            # 골든 크로스: 빠른 MA가 느린 MA를 상향 돌파
            if (
                self.prev_fast_ma <= self.prev_slow_ma
                and fast_ma > slow_ma
                and not self.position_open
            ):
                signal = "long"
                self.position_open = True

            # 데드 크로스: 빠른 MA가 느린 MA를 하향 돌파
            elif (
                self.prev_fast_ma >= self.prev_slow_ma
                and fast_ma < slow_ma
                and self.position_open
            ):
                signal = "close"
                self.position_open = False

        # 현재 값을 이전 값으로 저장
        self.prev_fast_ma = fast_ma
        self.prev_slow_ma = slow_ma

        return signal

    def reset(self):
        """전략 상태 초기화"""
        self.prev_fast_ma = None
        self.prev_slow_ma = None
        self.position_open = False


def create_strategy_function(strategy: GoldenCrossStrategy):
    """
    백테스팅 엔진에서 사용할 전략 함수 생성

    Args:
        strategy: GoldenCrossStrategy 인스턴스

    Returns:
        row를 받아서 시그널을 반환하는 함수
    """
    strategy.reset()  # 전략 초기화
    return lambda row: strategy.generate_signal(row)
