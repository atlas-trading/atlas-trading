"""
전략 사용 예시

동일한 Strategy 객체를 백테스트와 실거래 모두에서 사용하는 방법을 보여줍니다.
"""

import pandas as pd
from datetime import datetime, timedelta

# 전략 import
from app.strategies import GoldenCrossStrategy, RSIStrategy

# 백테스팅 엔진
from app.backtesting.engine import BacktestEngine

# 실거래 봇 (향후 구현)
# from app.trading.live_bot import LiveTradingBot


def example_backtest():
    """백테스트 예시"""
    print("=" * 60)
    print("1. 백테스트 예시")
    print("=" * 60)

    # 1. 전략 생성
    strategy = GoldenCrossStrategy(fast_period=10, slow_period=30, ma_type='sma')

    print(f"전략: {strategy.get_name()}")
    print(f"파라미터: {strategy.get_parameters()}")
    print()

    # 2. 샘플 데이터 생성 (실제로는 API에서 가져옴)
    dates = pd.date_range(start='2024-01-01', periods=300, freq='1D')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + pd.Series(range(300)).cumsum() * 10,
        'high': 50500 + pd.Series(range(300)).cumsum() * 10,
        'low': 49500 + pd.Series(range(300)).cumsum() * 10,
        'close': 50000 + pd.Series(range(300)).cumsum() * 10,
        'volume': 1000,
    })

    # 3. 백테스트 실행
    engine = BacktestEngine(initial_capital=10000, commission=0.001)

    results = engine.run(
        df=df,
        strategy=strategy,  # Strategy 객체 전달
        symbol='BTC/USDT',
        timeframe='1d'
    )

    # 4. 결과 출력
    print(f"총 수익률: {results['total_return']:.2f}%")
    print(f"최종 자본: ${results['final_capital']:.2f}")
    print(f"최대 낙폭: {results['max_drawdown']:.2f}%")
    print(f"샤프 비율: {results['sharpe_ratio']:.2f}")
    print(f"총 거래: {results['total_trades']}")
    print(f"승률: {results['win_rate']:.1f}%")
    print()


def example_live_trading():
    """실거래 예시 (동일한 전략 사용)"""
    print("=" * 60)
    print("2. 실거래 예시 (동일한 전략 사용)")
    print("=" * 60)

    # 1. 백테스트에서 사용한 것과 동일한 전략 생성
    strategy = GoldenCrossStrategy(fast_period=10, slow_period=30, ma_type='sma')

    print(f"전략: {strategy.get_name()}")
    print(f"파라미터: {strategy.get_parameters()}")
    print()

    print("실거래 봇 코드 예시:")
    print("""
    from app.trading.live_bot import LiveTradingBot

    # 백테스트와 동일한 전략 객체 사용!
    bot = LiveTradingBot(
        exchange='binance',
        api_key='YOUR_API_KEY',
        api_secret='YOUR_API_SECRET',
        strategy=strategy,  # ← 백테스트와 동일한 객체
        symbol='BTC/USDT',
        timeframe='1h',
        initial_capital=10000.0,
    )

    bot.start()  # 실거래 시작
    """)
    print()


def example_custom_strategy():
    """커스텀 전략 만들기"""
    print("=" * 60)
    print("3. 새로운 전략 추가하기")
    print("=" * 60)

    print("""
새 전략을 만들려면 Strategy 클래스를 상속받아 구현하면 됩니다:

# app/strategies/my_strategy.py

from app.strategies.base import Strategy, IndicatorMixin, SignalType
import pandas as pd

class MyCustomStrategy(Strategy, IndicatorMixin):
    def __init__(self, my_param1=10, my_param2=20):
        super().__init__()
        self.my_param1 = my_param1
        self.my_param2 = my_param2

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # 필요한 지표 추가
        df = self.add_sma(df, self.my_param1)
        df = self.add_rsi(df, self.my_param2)
        return df

    def on_bar(self, row: pd.Series) -> SignalType:
        # 시그널 로직
        if row['rsi'] < 30 and not self.has_position:
            return 'long'
        elif row['rsi'] > 70 and self.has_position:
            return 'close'
        return None

# 사용법 (백테스트와 실거래 모두 동일)
strategy = MyCustomStrategy(my_param1=15, my_param2=14)

# 백테스트
engine.run(df, strategy=strategy, ...)

# 실거래
bot = LiveTradingBot(..., strategy=strategy)
bot.start()
    """)
    print()


def example_multiple_strategies():
    """여러 전략 비교"""
    print("=" * 60)
    print("4. 여러 전략 비교하기")
    print("=" * 60)

    # 샘플 데이터
    dates = pd.date_range(start='2024-01-01', periods=300, freq='1D')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + pd.Series(range(300)).cumsum() * 10,
        'high': 50500 + pd.Series(range(300)).cumsum() * 10,
        'low': 49500 + pd.Series(range(300)).cumsum() * 10,
        'close': 50000 + pd.Series(range(300)).cumsum() * 10,
        'volume': 1000,
    })

    # 여러 전략 생성
    strategies = [
        GoldenCrossStrategy(fast_period=10, slow_period=30),
        GoldenCrossStrategy(fast_period=20, slow_period=50),
        RSIStrategy(rsi_period=14, oversold_level=30, overbought_level=70),
    ]

    engine = BacktestEngine(initial_capital=10000)

    # 각 전략 백테스트
    for strategy in strategies:
        results = engine.run(df, strategy=strategy, symbol='BTC/USDT', timeframe='1d')

        print(f"전략: {strategy.get_name()}")
        print(f"  파라미터: {strategy.get_parameters()}")
        print(f"  수익률: {results['total_return']:+.2f}%")
        print(f"  샤프 비율: {results['sharpe_ratio']:.2f}")
        print(f"  거래 횟수: {results['total_trades']}")
        print()


if __name__ == "__main__":
    # 예시 실행
    example_backtest()
    example_live_trading()
    example_custom_strategy()
    example_multiple_strategies()

    print("=" * 60)
    print("핵심 포인트:")
    print("=" * 60)
    print("✅ 하나의 Strategy 클래스를 만들면")
    print("✅ 백테스트와 실거래 모두에서 동일하게 사용 가능")
    print("✅ 전략 로직을 한 곳에서만 관리")
    print("✅ 새 전략 추가가 간단함 (Strategy 상속)")
