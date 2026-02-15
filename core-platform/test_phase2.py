"""
Phase 2 기능 테스트 스크립트

새로운 Strategy 클래스와 고급 분석 기능을 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.strategies import GoldenCrossStrategy, RSIStrategy
from app.backtesting.engine import BacktestEngine
from app.analytics.summary import calculate_advanced_metrics
from app.analytics.trade_analysis import analyze_trades
import requests


def generate_sample_data(days=365, start_price=50000):
    """샘플 OHLCV 데이터 생성"""
    print("📊 샘플 데이터 생성 중...")

    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='1D')

    # 랜덤 워크 + 트렌드
    trend = np.linspace(0, 5000, days)
    noise = np.random.randn(days).cumsum() * 100
    close_prices = start_price + trend + noise

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(days) * 50,
        'high': close_prices + np.abs(np.random.randn(days)) * 100,
        'low': close_prices - np.abs(np.random.randn(days)) * 100,
        'close': close_prices,
        'volume': np.random.randint(1000, 5000, days),
    })

    print(f"✅ {len(df)}일 데이터 생성 완료")
    return df


def test_golden_cross_strategy():
    """골든 크로스 전략 테스트"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Golden Cross Strategy")
    print("="*60)

    # 1. 전략 생성
    strategy = GoldenCrossStrategy(fast_period=10, slow_period=30, ma_type='sma')
    print(f"전략: {strategy.get_name()}")
    print(f"파라미터: {strategy.get_parameters()}")

    # 2. 샘플 데이터
    df = generate_sample_data(days=300)

    # 3. 백테스트 실행
    print("\n🚀 백테스트 실행 중...")
    backtest_engine = BacktestEngine(initial_capital=10000, commission=0.001)

    results = backtest_engine.run(
        df=df,
        strategy=strategy,
        symbol='BTC/USDT',
        timeframe='1d'
    )

    # 4. 결과 출력
    print("\n📈 백테스트 결과:")
    print(f"  총 수익률: {results['total_return']:.2f}%")
    print(f"  최종 자본: ${results['final_capital']:,.2f}")
    print(f"  최대 낙폭: {results['max_drawdown']:.2f}%")
    print(f"  샤프 비율: {results['sharpe_ratio']:.2f}")
    print(f"  총 거래: {results['total_trades']}")
    print(f"  승률: {results['win_rate']:.1f}%")

    # 5. 고급 지표 계산
    print("\n📊 고급 지표 계산 중...")
    advanced = calculate_advanced_metrics(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        total_return=results['total_return'],
        max_drawdown=results['max_drawdown'],
        initial_capital=results['initial_capital'],
        start_date=str(results['start_date']),
        end_date=str(results['end_date']),
    )

    print("\n💎 고급 성과 지표:")
    print(f"  Sortino Ratio: {advanced['sortino_ratio']:.2f}")
    print(f"  Calmar Ratio: {advanced['calmar_ratio']:.2f}")
    print(f"  Profit Factor: {advanced['profit_factor']:.2f}")
    print(f"  Expectancy: ${advanced['expectancy']:.2f}")
    print(f"  Win/Loss Ratio: {advanced['win_loss_ratio']:.2f}")
    print(f"  최대 연속 승리: {advanced['max_consecutive_wins']}")
    print(f"  최대 연속 손실: {advanced['max_consecutive_losses']}")

    # 6. 거래 분석
    print("\n🔍 거래 분석 중...")
    trade_analysis = analyze_trades(
        trades=results['trades'],
        df=df,
        initial_capital=results['initial_capital'],
    )

    holding = trade_analysis.get('holding_periods', {})
    distribution = trade_analysis.get('distribution', {})

    print("\n⏱️ 보유 기간 분석:")
    print(f"  평균: {holding.get('avg_holding_hours', 0):.1f}시간")
    print(f"  중앙값: {holding.get('median_holding_hours', 0):.1f}시간")

    print("\n💰 손익 분포:")
    print(f"  평균 손익: ${distribution.get('avg_pnl', 0):.2f}")
    print(f"  최대 승리: ${distribution.get('largest_win', 0):.2f}")
    print(f"  최대 손실: ${distribution.get('largest_loss', 0):.2f}")

    # 7. API로 결과 전송 (데이터베이스 저장은 api-server에서 처리)
    print("\n✅ 백테스트 완료!")
    print("\n💡 API를 통해 데이터를 저장하려면 api-server의 엔드포인트를 사용하세요.")
    return None


def test_rsi_strategy():
    """RSI 전략 테스트"""
    print("\n" + "="*60)
    print("🧪 TEST 2: RSI Strategy")
    print("="*60)

    # 1. 전략 생성
    strategy = RSIStrategy(rsi_period=14, oversold_level=30, overbought_level=70)
    print(f"전략: {strategy.get_name()}")
    print(f"파라미터: {strategy.get_parameters()}")

    # 2. 샘플 데이터
    df = generate_sample_data(days=300)

    # 3. 백테스트 실행
    print("\n🚀 백테스트 실행 중...")
    backtest_engine = BacktestEngine(initial_capital=10000, commission=0.001)

    results = backtest_engine.run(
        df=df,
        strategy=strategy,
        symbol='BTC/USDT',
        timeframe='1d'
    )

    # 4. 결과 출력
    print("\n📈 백테스트 결과:")
    print(f"  총 수익률: {results['total_return']:.2f}%")
    print(f"  최종 자본: ${results['final_capital']:,.2f}")
    print(f"  최대 낙폭: {results['max_drawdown']:.2f}%")
    print(f"  샤프 비율: {results['sharpe_ratio']:.2f}")
    print(f"  총 거래: {results['total_trades']}")
    print(f"  승률: {results['win_rate']:.1f}%")

    # 5. 백테스트 완료
    print("\n✅ 백테스트 완료!")
    return None


def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*30)
    print("Phase 2 기능 테스트 시작")
    print("🚀"*30 + "\n")

    try:
        # Test 1: Golden Cross
        bt1_id = test_golden_cross_strategy()

        # Test 2: RSI
        bt2_id = test_rsi_strategy()

        # 결과 요약
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        print("\n📱 대시보드에서 확인하세요:")
        print(f"   - 목록: http://localhost:5173/backtests")
        print(f"   - 비교: http://localhost:5173/compare")

        print("\n🎯 테스트할 기능:")
        print("   1. 백테스트 목록 페이지")
        print("   2. 백테스트 상세 페이지 - 개요 탭")
        print("   3. 백테스트 상세 페이지 - 고급 지표 탭 (NEW!)")
        print("   4. 백테스트 상세 페이지 - 거래 분석 탭 (NEW!)")
        print("   5. 백테스트 비교 페이지 (NEW!)")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
