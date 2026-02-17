"""
백테스팅 엔진 테스트

BacktestEngine의 핵심 기능을 검증합니다.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List

from app.backtesting.engine import BacktestEngine, Position
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema


class SimpleLongStrategy(Strategy):
    """테스트용 간단한 롱 전략"""

    def __init__(self, entry_threshold: int = 5, **kwargs):
        super().__init__(entry_threshold=entry_threshold, **kwargs)
        self.bar_count = 0

    def on_bar(self, row: pd.Series) -> Signal:
        self.bar_count += 1

        # 5번째 바에서 진입
        if self.bar_count == self.entry_threshold and not self.has_position:
            return Signal(action='long', symbol=self.symbol, size=1.0)

        # 10번째 바에서 청산
        if self.bar_count == 10 and self.has_position:
            return Signal(action='close', symbol=self.symbol)

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=20)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        return [
            {'name': 'entry_threshold', 'type': 'int', 'default': 5, 'min': 1, 'max': 100,
             'description': 'Entry bar number', 'required': True}
        ]


class TestPosition:
    """Position 클래스 테스트"""

    def test_position_initialization(self):
        """포지션 초기화 테스트"""
        pos = Position()

        assert pos.side is None
        assert pos.entry_price == 0.0
        assert pos.quantity == 0.0
        assert pos.is_open() == False

    def test_position_open_long(self):
        """롱 포지션 오픈 테스트"""
        pos = Position()
        timestamp = datetime.now()

        pos.open('long', 50000.0, 0.1, timestamp, position_size_pct=0.5)

        assert pos.is_open() == True
        assert pos.side == 'long'
        assert pos.entry_price == 50000.0
        assert pos.quantity == 0.1
        assert pos.position_size_pct == 0.5

    def test_position_close(self):
        """포지션 클로즈 테스트"""
        pos = Position()
        pos.open('long', 50000.0, 0.1, datetime.now())

        pos.close()

        assert pos.is_open() == False
        assert pos.side is None


class TestBacktestEngine:
    """BacktestEngine 테스트"""

    @pytest.fixture
    def sample_data(self):
        """테스트용 샘플 데이터 (가격 상승 추세)"""
        dates = pd.date_range('2024-01-01', periods=20, freq='1h')

        return pd.DataFrame({
            'timestamp': dates,
            'open': np.linspace(45000, 50000, 20),
            'high': np.linspace(45500, 50500, 20),
            'low': np.linspace(44500, 49500, 20),
            'close': np.linspace(45000, 50000, 20),  # 10% 상승
            'volume': np.random.uniform(100, 1000, 20)
        })

    def test_engine_initialization(self):
        """엔진 초기화 테스트"""
        engine = BacktestEngine(
            initial_capital=10000,
            commission=0.001,
            use_kelly_sizing=False
        )

        assert engine.initial_capital == 10000
        assert engine.commission == 0.001
        assert engine.cash == 10000
        assert engine.position.is_open() == False

    def test_execute_long_and_close(self, sample_data):
        """롱 진입 및 청산 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)

        # 롱 진입 (45000)
        engine.execute_long(45000, sample_data['timestamp'].iloc[0], size_pct=1.0)

        assert engine.position.is_open() == True
        assert engine.position.side == 'long'
        assert engine.cash < 10000  # 수수료 차감

        # 청산 (50000)
        trade = engine.close_position(50000, sample_data['timestamp'].iloc[10])

        assert engine.position.is_open() == False
        assert trade is not None
        assert trade['pnl'] > 0  # 수익
        assert trade['side'] == 'long'

    def test_calculate_equity(self):
        """자산 계산 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.0)

        # 롱 진입
        engine.execute_long(50000, datetime.now(), size_pct=1.0)

        # 가격 상승 시 자산 증가
        equity_at_55000 = engine.calculate_equity(55000)
        assert equity_at_55000 > 10000

        # 가격 하락 시 자산 감소
        equity_at_45000 = engine.calculate_equity(45000)
        assert equity_at_45000 < 10000

    def test_commission_deduction(self):
        """수수료 차감 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)

        initial_cash = engine.cash

        # 진입
        engine.execute_long(50000, datetime.now(), size_pct=1.0)

        # 수수료 차감 확인 (0.1%)
        expected_commission = 10000 * 0.001
        assert abs((initial_cash - engine.cash) - 10000) < expected_commission * 2  # 진입 수수료

        # 청산
        trade = engine.close_position(50000, datetime.now())

        # 청산 수수료도 차감됨
        assert trade['commission_paid'] > 0

    def test_kelly_criterion_calculation(self):
        """Kelly Criterion 계산 테스트"""
        engine = BacktestEngine(
            initial_capital=10000,
            use_kelly_sizing=True,
            kelly_window=10,
            kelly_fraction=0.5
        )

        # 거래 기록 추가 (승률 60%, 평균 승리 2%, 평균 손실 1%)
        for i in range(10):
            if i < 6:  # 승리
                engine.trades.append({'pnl': 100, 'pnl_pct': 2.0})
            else:  # 손실
                engine.trades.append({'pnl': -50, 'pnl_pct': -1.0})

        kelly = engine.calculate_kelly_fraction()

        # Kelly는 0.1 ~ 0.5 범위
        assert 0.1 <= kelly <= 0.5

    def test_run_with_strategy(self, sample_data):
        """전략을 사용한 백테스팅 실행 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)
        strategy = SimpleLongStrategy(symbol='BTC/USDT', entry_threshold=5)

        result = engine.run(
            df=sample_data,
            strategy=strategy,
            strategy_name='SimpleLongStrategy',
            symbol='BTC/USDT',
            timeframe='1h'
        )

        # 결과 검증
        assert result is not None
        assert 'strategy_name' in result
        assert 'final_capital' in result
        assert 'total_trades' in result
        assert 'equity_curve' in result

        # 최소 1개 거래 발생
        assert result['total_trades'] >= 1

        # 최종 자본이 초기 자본과 다름 (거래 발생)
        assert result['final_capital'] != result['initial_capital']

    def test_calculate_metrics(self, sample_data):
        """성과 지표 계산 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)
        strategy = SimpleLongStrategy(symbol='BTC/USDT')

        result = engine.run(
            df=sample_data,
            strategy=strategy,
            strategy_name='Test',
            symbol='BTC/USDT',
            timeframe='1h'
        )

        # 필수 지표 존재 확인
        assert 'total_return' in result
        assert 'max_drawdown' in result
        assert 'sharpe_ratio' in result
        assert 'win_rate' in result

        # 값 범위 검증
        assert -100 <= result['max_drawdown'] <= 0  # MDD는 음수

    def test_short_position(self):
        """숏 포지션 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.0, use_kelly_sizing=False)

        # 숏 진입 (50000)
        engine.execute_short(50000, datetime.now(), size_pct=1.0)

        assert engine.position.is_open() == True
        assert engine.position.side == 'short'

        # 가격 하락 시 수익
        trade = engine.close_position(45000, datetime.now())  # 10% 하락

        assert trade['pnl'] > 0  # 숏은 가격 하락 시 수익
        assert trade['side'] == 'short'

    def test_equity_curve_recording(self, sample_data):
        """Equity Curve 기록 테스트"""
        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)
        strategy = SimpleLongStrategy(symbol='BTC/USDT')

        result = engine.run(
            df=sample_data,
            strategy=strategy,
            strategy_name='Test',
            symbol='BTC/USDT',
            timeframe='1h'
        )

        equity_curve = result['equity_curve']

        # Equity curve가 기록되었는지 확인
        assert len(equity_curve) > 0

        # 첫 자산은 초기 자본
        assert equity_curve[0]['equity'] == 10000

        # 각 엔트리에 필요한 필드 존재
        for entry in equity_curve:
            assert 'timestamp' in entry
            assert 'equity' in entry
            assert 'cash' in entry
            assert 'position_value' in entry

    def test_multiple_trades(self):
        """여러 거래 실행 테스트"""

        class MultiTradeStrategy(Strategy):
            """여러 거래를 하는 전략"""
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.bar_count = 0

            def on_bar(self, row: pd.Series) -> Signal:
                self.bar_count += 1

                # 3번, 7번, 11번, 15번에 진입
                if self.bar_count in [3, 7, 11, 15] and not self.has_position:
                    return Signal(action='long', symbol=self.symbol, size=0.5)

                # 5번, 9번, 13번, 17번에 청산
                if self.bar_count in [5, 9, 13, 17] and self.has_position:
                    return Signal(action='close', symbol=self.symbol)

                return Signal(action='hold', symbol=self.symbol)

            def get_required_data(self) -> List[DataRequirement]:
                return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=20)]

            @classmethod
            def get_parameter_schema(cls) -> List[ParameterSchema]:
                return []

        # 테스트 데이터 (20개 바)
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=20, freq='1h'),
            'open': np.random.uniform(45000, 50000, 20),
            'high': np.random.uniform(50000, 51000, 20),
            'low': np.random.uniform(44000, 45000, 20),
            'close': np.linspace(45000, 50000, 20),  # 상승 추세
            'volume': np.random.uniform(100, 1000, 20)
        })

        engine = BacktestEngine(initial_capital=10000, commission=0.001, use_kelly_sizing=False)
        strategy = MultiTradeStrategy(symbol='BTC/USDT')

        result = engine.run(df, strategy, strategy_name='MultiTrade', symbol='BTC/USDT', timeframe='1h')

        # 최소 2개 이상의 거래
        assert result['total_trades'] >= 2

        # 거래 기록 확인
        trades = result['trades']
        assert len(trades) == result['total_trades']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
