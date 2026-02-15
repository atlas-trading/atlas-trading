"""
Kelly Sizing 작동 테스트
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.backtesting.engine import BacktestEngine
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.analytics.monte_carlo import monte_carlo_simulation


def generate_mock_data(n_days=100, seed=42):
    """Mock OHLCV 데이터 생성 - 승패가 섞이도록"""
    np.random.seed(seed)
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_days)]

    # 기본 가격: 여러 사인파 조합으로 복잡한 패턴 생성
    base = 50000
    wave1 = 3000 * np.sin(np.linspace(0, 8 * np.pi, n_days))
    wave2 = 2000 * np.sin(np.linspace(0, 20 * np.pi, n_days))
    wave3 = 1500 * np.sin(np.linspace(0, 35 * np.pi, n_days))

    prices = base + wave1 + wave2 + wave3

    # 큰 노이즈로 변동성 증가 (승패 유도)
    noise = np.random.normal(0, 1500, n_days)
    prices = prices + noise

    # 랜덤 점프/드롭 추가 (급등/급락)
    for _ in range(n_days // 20):
        idx = np.random.randint(10, n_days - 10)
        jump = np.random.choice([-3000, 3000])
        prices[idx:idx+5] += jump

    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(100, 1000, n_days)
    })

    return df


def main():
    print("=" * 60)
    print("Kelly Sizing Test")
    print("=" * 60)

    # Mock 데이터 생성
    df = generate_mock_data(n_days=500, seed=123)  # 승패가 섞이는 시드
    print(f"✓ Generated {len(df)} mock candles")

    # 전략 생성 (더 많은 신호를 위해 임계값 완화)
    strategy = RSIMeanReversionStrategy(
        rsi_period=10,  # 짧은 기간으로 더 민감하게
        oversold_threshold=40,  # 완화된 임계값
        overbought_threshold=60,  # 완화된 임계값
    )

    # Kelly sizing 활성화된 엔진 생성
    engine = BacktestEngine(
        initial_capital=10000.0,
        commission=0.001,
        use_kelly_sizing=True,
        kelly_window=20,
        kelly_fraction=0.5,
    )

    print(f"\n{'Engine Configuration:'}")
    print(f"  use_kelly_sizing: {engine.use_kelly_sizing}")
    print(f"  kelly_window: {engine.kelly_window}")
    print(f"  kelly_fraction: {engine.kelly_fraction}")

    print("\n" + "-" * 60)
    print("Running backtest...")
    print("-" * 60)

    # 백테스트 실행
    result = engine.run(
        df=df,
        strategy=strategy,
        strategy_name="RSI_Test",
        symbol="MOCK/USD",
        timeframe="1d",
    )

    # 결과 확인
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total Trades: {result['total_trades']}")
    print(f"Final Capital: ${result['final_capital']:,.2f}")
    print(f"Total Return: {result['total_return']:+.2f}%")

    # Position sizing 확인
    if result['trades']:
        print("\n" + "-" * 60)
        print("Position Sizing Analysis:")
        print("-" * 60)

        # 첫 5개, 중간 5개, 마지막 5개 보여주기
        n_trades = len(result['trades'])
        sample_indices = []

        if n_trades <= 15:
            sample_indices = range(n_trades)
        else:
            sample_indices = list(range(5)) + list(range(n_trades//2 - 2, n_trades//2 + 3)) + list(range(n_trades - 5, n_trades))

        for i in sample_indices:
            trade = result['trades'][i]
            pos_size = trade.get('position_size_pct', 1.0)
            pnl_pct = trade.get('pnl_pct', 0)
            print(f"  Trade #{i+1}: Position Size = {pos_size:.3f}, PnL = {pnl_pct:+.2f}%")

        if n_trades > 15:
            print(f"  ... ({n_trades - 15} trades omitted) ...")

        # 통계
        all_sizes = [t.get('position_size_pct', 1.0) for t in result['trades']]
        print(f"\nPosition Size Stats:")
        print(f"  Min: {min(all_sizes):.3f}")
        print(f"  Max: {max(all_sizes):.3f}")
        print(f"  Avg: {np.mean(all_sizes):.3f}")
        print(f"  Std: {np.std(all_sizes):.3f}")

        # Kelly sizing이 작동했는지 확인
        if all(s == 1.0 for s in all_sizes):
            print("\n⚠️  WARNING: All position sizes are 1.0 - Kelly sizing NOT working!")
        else:
            print("\n✓ Kelly sizing is WORKING - position sizes vary")

        # Monte Carlo 시뮬레이션 실행
        if len(result['trades']) >= 10:
            print("\n" + "=" * 60)
            print("MONTE CARLO SIMULATION")
            print("=" * 60)

            mc_result = monte_carlo_simulation(
                trades=result['trades'],
                initial_capital=10000.0,
                n_simulations=100,  # 빠른 테스트를 위해 100회
                n_sample_curves=5,
                use_dynamic_kelly=True,  # 동적 Kelly 재계산
                kelly_window=20,
                kelly_fraction=0.5,
            )

            print(f"\nFinal Capital Distribution:")
            print(f"  Min:    ${mc_result.final_capital_min:,.2f}")
            print(f"  5th:    ${mc_result.final_capital_5th:,.2f}")
            print(f"  Median: ${mc_result.final_capital_median:,.2f}")
            print(f"  95th:   ${mc_result.final_capital_95th:,.2f}")
            print(f"  Max:    ${mc_result.final_capital_max:,.2f}")

            print(f"\nTotal Return Distribution:")
            print(f"  5th:    {mc_result.total_return_5th:+.2f}%")
            print(f"  Median: {mc_result.total_return_median:+.2f}%")
            print(f"  95th:   {mc_result.total_return_95th:+.2f}%")

            # 발산 여부 확인
            spread = mc_result.final_capital_95th - mc_result.final_capital_5th
            spread_pct = (spread / mc_result.initial_capital) * 100

            print(f"\nSpread (95th - 5th): ${spread:,.2f} ({spread_pct:.1f}%)")

            if spread_pct > 5:
                print("✓ Monte Carlo paths DIVERGE (good - Kelly sizing working!)")
            else:
                print("⚠️  Monte Carlo paths converge (Kelly sizing may not be strong enough)")

    print("=" * 60)


if __name__ == '__main__':
    main()
