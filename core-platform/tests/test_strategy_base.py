"""
Strategy Base 클래스 테스트

전략 인터페이스의 핵심 기능을 검증합니다.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List

from app.strategies.base import (
    Strategy,
    Signal,
    DataRequirement,
    ParameterSchema,
    IndicatorMixin
)


class DummyStrategy(Strategy, IndicatorMixin):
    """테스트용 더미 전략"""

    def __init__(self, period: int = 20, threshold: float = 0.5, **kwargs):
        super().__init__(
            period=period,
            threshold=threshold,
            **kwargs
        )

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """SMA 추가"""
        df = self.add_sma(df, self.period)
        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """간단한 SMA 크로스오버 전략"""
        if pd.isna(row.get(f'sma_{self.period}')):
            return Signal(action='hold', symbol=self.symbol)

        if not self.has_position and row['close'] > row[f'sma_{self.period}'] * (1 + self.threshold / 100):
            return Signal(
                action='long',
                symbol=self.symbol,
                size=0.5,
                confidence=0.8,
                reason='Price above SMA'
            )
        elif self.has_position and row['close'] < row[f'sma_{self.period}']:
            return Signal(
                action='close',
                symbol=self.symbol,
                reason='Price below SMA'
            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=100)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        return [
            {
                'name': 'period',
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 100,
                'description': 'SMA period',
                'required': True
            },
            {
                'name': 'threshold',
                'type': 'float',
                'default': 0.5,
                'min': 0.0,
                'max': 5.0,
                'step': 0.1,
                'description': 'Entry threshold (%)',
                'required': True
            }
        ]


class TestStrategyBase:
    """Strategy 베이스 클래스 테스트"""

    def test_strategy_initialization(self):
        """전략 초기화 테스트"""
        strategy = DummyStrategy(symbol='BTC/USDT', period=30, threshold=1.0)

        assert strategy.symbol == 'BTC/USDT'
        assert strategy.period == 30
        assert strategy.threshold == 1.0
        assert strategy.has_position == False
        assert strategy.position_side is None

    def test_parameter_validation_success(self):
        """파라미터 검증 성공 케이스"""
        strategy = DummyStrategy()

        valid_params = {'period': 50, 'threshold': 2.0}
        errors = strategy.validate_parameters(valid_params)

        assert len(errors) == 0

    def test_parameter_validation_out_of_range(self):
        """파라미터 범위 초과 검증"""
        strategy = DummyStrategy()

        invalid_params = {'period': 200, 'threshold': 10.0}  # 범위 초과
        errors = strategy.validate_parameters(invalid_params)

        assert 'period' in errors
        assert 'threshold' in errors

    def test_parameter_validation_missing_required(self):
        """필수 파라미터 누락 검증"""
        strategy = DummyStrategy()

        invalid_params = {}  # 필수 파라미터 없음
        errors = strategy.validate_parameters(invalid_params)

        # period, threshold 둘 다 required=True
        assert 'period' in errors or 'threshold' in errors

    def test_get_parameters(self):
        """파라미터 조회 테스트"""
        strategy = DummyStrategy(symbol='ETH/USDT', period=25, threshold=1.5)

        params = strategy.get_parameters()

        assert params['symbol'] == 'ETH/USDT'
        assert params['period'] == 25
        assert params['threshold'] == 1.5

    def test_update_parameters(self):
        """파라미터 업데이트 테스트"""
        strategy = DummyStrategy(period=20, threshold=0.5)

        # 업데이트
        strategy.update_parameters({'period': 30, 'threshold': 1.0})

        assert strategy.period == 30
        assert strategy.threshold == 1.0

    def test_update_parameters_invalid(self):
        """잘못된 파라미터 업데이트 실패"""
        strategy = DummyStrategy()

        with pytest.raises(ValueError, match="Parameter validation failed"):
            strategy.update_parameters({'period': 200})  # 범위 초과

    def test_reset(self):
        """전략 상태 초기화 테스트"""
        strategy = DummyStrategy()

        # 상태 변경
        strategy.has_position = True
        strategy.position_side = 'long'
        strategy.bars_since_entry = 10

        # 초기화
        strategy.reset()

        assert strategy.has_position == False
        assert strategy.position_side is None
        assert strategy.bars_since_entry == 0

    def test_on_position_opened(self):
        """포지션 진입 콜백 테스트"""
        strategy = DummyStrategy()

        strategy.on_position_opened('long', 50000.0, datetime.now())

        assert strategy.has_position == True
        assert strategy.position_side == 'long'
        assert strategy.bars_since_entry == 0

    def test_on_position_closed(self):
        """포지션 청산 콜백 테스트"""
        strategy = DummyStrategy()
        strategy.has_position = True
        strategy.position_side = 'long'

        strategy.on_position_closed(100.0, 2.0, datetime.now())

        assert strategy.has_position == False
        assert strategy.position_side is None

    def test_prepare_data_adds_indicators(self):
        """데이터 전처리 (지표 추가) 테스트"""
        strategy = DummyStrategy(period=10)

        # 테스트 데이터 생성
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1h'),
            'open': np.random.uniform(45000, 50000, 50),
            'high': np.random.uniform(50000, 51000, 50),
            'low': np.random.uniform(44000, 45000, 50),
            'close': np.random.uniform(45000, 50000, 50),
            'volume': np.random.uniform(100, 1000, 50)
        })

        df_prepared = strategy.prepare_data(df.copy())

        # SMA 컬럼이 추가되었는지 확인
        assert f'sma_{strategy.period}' in df_prepared.columns

        # 계산 검증 (10번째 행부터 값이 있어야 함)
        assert pd.notna(df_prepared[f'sma_{strategy.period}'].iloc[strategy.period])

    def test_signal_generation(self):
        """시그널 생성 테스트"""
        strategy = DummyStrategy(period=10, threshold=1.0)

        # 테스트 데이터
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1h'),
            'close': [45000] * 20 + [50000] * 30  # 가격 급등
        })
        df = strategy.prepare_data(df)

        # 시그널 생성
        signals = []
        for _, row in df.iterrows():
            signal = strategy.on_bar(row)
            signals.append(signal)
            strategy.on_bar_update()

        # 롱 진입 시그널이 있어야 함
        long_signals = [s for s in signals if s.action == 'long']
        assert len(long_signals) > 0

        # 시그널 속성 검증
        for signal in long_signals:
            assert signal.symbol == strategy.symbol
            assert 0 <= signal.size <= 1.0
            assert 0 <= signal.confidence <= 1.0


class TestIndicatorMixin:
    """IndicatorMixin 테스트"""

    @pytest.fixture
    def sample_df(self):
        """테스트용 샘플 데이터"""
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
            'open': np.random.uniform(45000, 50000, 100),
            'high': np.random.uniform(50000, 51000, 100),
            'low': np.random.uniform(44000, 45000, 100),
            'close': np.random.uniform(45000, 50000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

    def test_add_sma(self, sample_df):
        """SMA 추가 테스트"""
        df = IndicatorMixin.add_sma(sample_df.copy(), period=20)

        assert 'sma_20' in df.columns
        assert pd.notna(df['sma_20'].iloc[20])

        # 수동 계산과 비교
        expected_sma = df['close'].iloc[10:30].mean()
        assert abs(df['sma_20'].iloc[29] - expected_sma) < 0.01

    def test_add_ema(self, sample_df):
        """EMA 추가 테스트"""
        df = IndicatorMixin.add_ema(sample_df.copy(), period=20)

        assert 'ema_20' in df.columns
        assert pd.notna(df['ema_20'].iloc[20])

    def test_add_rsi(self, sample_df):
        """RSI 추가 테스트"""
        df = IndicatorMixin.add_rsi(sample_df.copy(), period=14)

        assert 'rsi_14' in df.columns

        # RSI는 0~100 범위
        rsi_values = df['rsi_14'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()

    def test_add_bollinger_bands(self, sample_df):
        """볼린저 밴드 추가 테스트"""
        df = IndicatorMixin.add_bollinger_bands(sample_df.copy(), period=20, std_dev=2.0)

        assert 'bb_middle' in df.columns
        assert 'bb_upper' in df.columns
        assert 'bb_lower' in df.columns

        # upper > middle > lower
        valid_rows = df[['bb_upper', 'bb_middle', 'bb_lower']].dropna()
        assert (valid_rows['bb_upper'] >= valid_rows['bb_middle']).all()
        assert (valid_rows['bb_middle'] >= valid_rows['bb_lower']).all()

    def test_add_macd(self, sample_df):
        """MACD 추가 테스트"""
        df = IndicatorMixin.add_macd(sample_df.copy())

        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_hist' in df.columns

    def test_add_atr(self, sample_df):
        """ATR 추가 테스트"""
        df = IndicatorMixin.add_atr(sample_df.copy(), period=14)

        assert 'atr_14' in df.columns

        # ATR은 항상 양수
        atr_values = df['atr_14'].dropna()
        assert (atr_values > 0).all()


class TestSignal:
    """Signal 데이터 클래스 테스트"""

    def test_signal_creation(self):
        """Signal 생성 테스트"""
        signal = Signal(
            action='long',
            symbol='BTC/USDT',
            size=0.5,
            stop_loss=0.98,
            take_profit=1.05,
            reason='Test signal',
            confidence=0.85
        )

        assert signal.action == 'long'
        assert signal.symbol == 'BTC/USDT'
        assert signal.size == 0.5
        assert signal.stop_loss == 0.98
        assert signal.take_profit == 1.05
        assert signal.confidence == 0.85

    def test_signal_to_dict(self):
        """Signal 딕셔너리 변환 테스트"""
        signal = Signal(action='close', symbol='ETH/USDT')

        signal_dict = signal.to_dict()

        assert isinstance(signal_dict, dict)
        assert signal_dict['action'] == 'close'
        assert signal_dict['symbol'] == 'ETH/USDT'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
