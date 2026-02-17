"""전략 최적화 및 개선 스크립트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import itertools
from typing import List, Dict, Any
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.strategies.statistical_arbitrage import StatisticalArbitrageStrategy
from app.strategies.ict_smart_money import ICTSmartMoneyStrategy
from app.strategies.adaptive_grid_trading import AdaptiveGridTradingStrategy
from app.strategies.market_microstructure import MarketMicrostructureStrategy


# 성공한 심볼 (ATOM, MATIC 제외)
SUCCESS_SYMBOLS = ['XRPUSDT', 'ETHUSDT', 'LINKUSDT', 'BNBUSDT', 'BTCUSDT', 'ADAUSDT']

# 테스트할 심볼
TEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT',
                'AVAXUSDT', 'DOTUSDT', 'LINKUSDT']


def optimize_statistical_arbitrage():
    """Statistical Arbitrage 최적화"""

    print("\n" + "=" * 120)
    print("🎯 Statistical Arbitrage 최적화")
    print("=" * 120)
    print(f"\n성공한 6개 심볼로 파라미터 최적화: {SUCCESS_SYMBOLS}\n")

    # 파라미터 그리드
    param_grid = {
        'zscore_entry_threshold': [1.5, 2.0, 2.5],
        'zscore_exit_threshold': [0.3, 0.5],
        'adx_trend_threshold': [25, 30, 35],
    }

    results = []

    for symbol in SUCCESS_SYMBOLS:
        print(f"\n{'#' * 100}")
        print(f"# {symbol}")
        print(f"{'#' * 100}\n")

        best_result = None
        best_return = -999

        # 모든 파라미터 조합 테스트
        param_combinations = list(itertools.product(
            param_grid['zscore_entry_threshold'],
            param_grid['zscore_exit_threshold'],
            param_grid['adx_trend_threshold']
        ))

        for idx, (entry_threshold, exit_threshold, adx_threshold) in enumerate(param_combinations, 1):
            print(f"  [{idx}/{len(param_combinations)}] ", end='', flush=True)
            print(f"Entry={entry_threshold}, Exit={exit_threshold}, ADX={adx_threshold} ", end='', flush=True)

            try:
                # 데이터 다운로드
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)

                fetcher = DataFetcher(exchange_id="binance")
                df = fetcher.fetch_ohlcv(symbol=symbol, timeframe='1d',
                                        start_date=start_date, end_date=end_date)

                if df.empty or len(df) < 100:
                    print("❌ 데이터 부족")
                    continue

                # 전략 실행
                strategy = StatisticalArbitrageStrategy(
                    symbol=symbol,
                    zscore_entry_threshold=entry_threshold,
                    zscore_exit_threshold=exit_threshold,
                    adx_trend_threshold=adx_threshold
                )
                df = strategy.prepare_data(df)

                engine = BacktestEngine(initial_capital=10000, commission=0.0004)
                result = engine.run(df=df, strategy=strategy, symbol=symbol, timeframe='1d')

                if result['total_trades'] > 0:
                    total_return = result['total_return']
                    sharpe = result['sharpe_ratio']
                    trades = result['total_trades']

                    emoji = "🟢" if total_return > 0 else "🔴"
                    print(f"{emoji} {total_return:>7.2f}%  샤프: {sharpe:>5.2f}  거래: {trades:>3}개")

                    # 최고 성과 업데이트
                    if total_return > best_return and trades >= 2:  # 최소 2개 거래
                        best_return = total_return
                        best_result = {
                            'symbol': symbol,
                            'entry_threshold': entry_threshold,
                            'exit_threshold': exit_threshold,
                            'adx_threshold': adx_threshold,
                            'total_return': total_return,
                            'sharpe_ratio': sharpe,
                            'total_trades': trades,
                            'win_rate': result['win_rate'],
                        }
                else:
                    print("⚪ 거래 없음")

            except Exception as e:
                print(f"❌ 에러: {e}")

            time.sleep(0.3)

        if best_result:
            results.append(best_result)
            print(f"\n✅ {symbol} 최적 파라미터:")
            print(f"   Entry Threshold: {best_result['entry_threshold']}")
            print(f"   Exit Threshold: {best_result['exit_threshold']}")
            print(f"   ADX Threshold: {best_result['adx_threshold']}")
            print(f"   수익률: {best_result['total_return']:.2f}%")
            print(f"   샤프: {best_result['sharpe_ratio']:.2f}")
            print(f"   거래: {best_result['total_trades']}개")

    return results


def fix_ict_smart_money():
    """ICT Smart Money 조건 완화 및 테스트"""

    print("\n" + "=" * 120)
    print("🔧 ICT Smart Money 조건 완화")
    print("=" * 120)
    print("\n조건 완화 버전 테스트:\n")

    # 완화된 파라미터
    relaxed_params = [
        {'swing_lookback': 7, 'fvg_min_size': 0.0015, 'liquidity_raid_tolerance': 0.003},
        {'swing_lookback': 5, 'fvg_min_size': 0.001, 'liquidity_raid_tolerance': 0.005},
    ]

    results = []

    for idx, params in enumerate(relaxed_params, 1):
        print(f"\n파라미터 세트 {idx}: swing={params['swing_lookback']}, "
              f"fvg={params['fvg_min_size']}, raid={params['liquidity_raid_tolerance']}\n")

        for symbol in TEST_SYMBOLS[:5]:  # 상위 5개만
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)

                fetcher = DataFetcher(exchange_id="binance")
                df = fetcher.fetch_ohlcv(symbol=symbol, timeframe='1d',
                                        start_date=start_date, end_date=end_date)

                if df.empty or len(df) < 100:
                    continue

                strategy = ICTSmartMoneyStrategy(symbol=symbol, **params)
                df = strategy.prepare_data(df)

                engine = BacktestEngine(initial_capital=10000, commission=0.0004)
                result = engine.run(df=df, strategy=strategy, symbol=symbol, timeframe='1d')

                print(f"  {symbol:<12} ", end='', flush=True)

                if result['total_trades'] > 0:
                    emoji = "🟢" if result['total_return'] > 0 else "🔴"
                    print(f"{emoji} 수익률: {result['total_return']:>7.2f}%  "
                          f"거래: {result['total_trades']:>3}개  승률: {result['win_rate']:>5.1f}%")

                    results.append({
                        'symbol': symbol,
                        'params': params,
                        'total_return': result['total_return'],
                        'total_trades': result['total_trades'],
                        'win_rate': result['win_rate'],
                    })
                else:
                    print("⚪ 거래 없음")

            except Exception as e:
                print(f"❌ 에러: {e}")

            time.sleep(0.3)

    return results


def fix_adaptive_grid():
    """Adaptive Grid Trading 파라미터 조정"""

    print("\n" + "=" * 120)
    print("🔧 Adaptive Grid Trading 파라미터 조정")
    print("=" * 120)
    print("\n개선된 파라미터 테스트:\n")

    # 개선 파라미터 (승률 향상 목표)
    improved_params = [
        {'grid_spacing_atr_multiplier': 0.3, 'num_grid_levels': 7, 'max_position_size': 1.0},
        {'grid_spacing_atr_multiplier': 0.4, 'num_grid_levels': 5, 'max_position_size': 0.9},
    ]

    results = []

    for idx, params in enumerate(improved_params, 1):
        print(f"\n파라미터 세트 {idx}: spacing={params['grid_spacing_atr_multiplier']}, "
              f"levels={params['num_grid_levels']}, max_pos={params['max_position_size']}\n")

        for symbol in ['BNBUSDT', 'XRPUSDT', 'DOTUSDT']:  # 수익났던 3개
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)

                fetcher = DataFetcher(exchange_id="binance")
                df = fetcher.fetch_ohlcv(symbol=symbol, timeframe='4h',
                                        start_date=start_date, end_date=end_date)

                if df.empty or len(df) < 100:
                    continue

                strategy = AdaptiveGridTradingStrategy(symbol=symbol, **params)
                df = strategy.prepare_data(df)

                engine = BacktestEngine(initial_capital=10000, commission=0.0004)
                result = engine.run(df=df, strategy=strategy, symbol=symbol, timeframe='4h')

                print(f"  {symbol:<12} ", end='', flush=True)

                if result['total_trades'] > 10:  # 최소 10개 거래
                    emoji = "🟢" if result['total_return'] > 0 else "🔴"
                    print(f"{emoji} 수익률: {result['total_return']:>7.2f}%  "
                          f"거래: {result['total_trades']:>3}개  승률: {result['win_rate']:>5.1f}%")

                    results.append({
                        'symbol': symbol,
                        'params': params,
                        'total_return': result['total_return'],
                        'total_trades': result['total_trades'],
                        'win_rate': result['win_rate'],
                    })
                else:
                    print("⚪ 거래 부족")

            except Exception as e:
                print(f"❌ 에러: {e}")

            time.sleep(0.3)

    return results


def main():
    """메인 실행"""

    print("\n" + "=" * 120)
    print("🚀 전략 최적화 및 개선 시스템")
    print("=" * 120)
    print("\n작업:")
    print("  1️⃣  Statistical Arbitrage 최적화 (성공한 6개 심볼)")
    print("  2️⃣  ICT Smart Money 조건 완화")
    print("  3️⃣  Adaptive Grid Trading 파라미터 조정")
    print()

    # 1. Statistical Arbitrage 최적화
    stat_arb_results = optimize_statistical_arbitrage()

    # 2. ICT 개선
    ict_results = fix_ict_smart_money()

    # 3. Grid 개선
    grid_results = fix_adaptive_grid()

    # 결과 요약
    print("\n" + "=" * 120)
    print("📊 최적화 결과 요약")
    print("=" * 120)

    if stat_arb_results:
        print("\n✅ Statistical Arbitrage 최적 파라미터:")
        for r in stat_arb_results:
            print(f"\n  {r['symbol']}:")
            print(f"    Entry Threshold: {r['entry_threshold']}")
            print(f"    Exit Threshold: {r['exit_threshold']}")
            print(f"    ADX Threshold: {r['adx_threshold']}")
            print(f"    수익률: {r['total_return']:.2f}%, 샤프: {r['sharpe_ratio']:.2f}, 거래: {r['total_trades']}개")

    if ict_results:
        print("\n✅ ICT Smart Money 개선 결과:")
        successful = [r for r in ict_results if r['total_trades'] > 0]
        if successful:
            for r in successful:
                print(f"  {r['symbol']}: {r['total_return']:.2f}% ({r['total_trades']}개 거래)")
        else:
            print("  ⚠️  여전히 거래 없음 - 추가 조정 필요")

    if grid_results:
        print("\n✅ Adaptive Grid 개선 결과:")
        profitable = [r for r in grid_results if r['total_return'] > 0]
        if profitable:
            for r in profitable:
                print(f"  {r['symbol']}: {r['total_return']:.2f}% (승률: {r['win_rate']:.1f}%)")
        else:
            print("  ⚠️  여전히 손실 - 추가 조정 필요")

    print("\n" + "=" * 120)
    print("✨ 최적화 완료!")
    print("=" * 120)


if __name__ == "__main__":
    main()
