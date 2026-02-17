"""프로페셔널 전략 백테스팅 실행 스크립트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.strategies.ict_smart_money import ICTSmartMoneyStrategy
from app.strategies.statistical_arbitrage import StatisticalArbitrageStrategy
from app.strategies.market_microstructure import MarketMicrostructureStrategy
from app.strategies.adaptive_grid_trading import AdaptiveGridTradingStrategy
from app.strategies.triangular_arbitrage import TriangularArbitrageStrategy


def run_single_backtest(strategy, symbol, timeframe, days, initial_capital=10000, commission=0.0004):
    """단일 전략 백테스트 실행"""

    print("\n" + "=" * 100)
    print(f"🚀 백테스팅 시작: {strategy.__class__.__name__}")
    print("=" * 100)

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print(f"  전략: {strategy.__class__.__name__}")
    print(f"  거래쌍: {symbol}")
    print(f"  타임프레임: {timeframe}")
    print(f"  기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"  초기 자본금: ${initial_capital:,.2f}")
    print(f"  수수료: {commission * 100:.2f}%")
    print()

    try:
        # 1. 데이터 다운로드
        print("📥 시장 데이터 다운로드 중...")
        fetcher = DataFetcher(exchange_id="binance")

        df = fetcher.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            print("❌ 데이터가 없습니다.")
            return None

        print(f"✅ {len(df)} 개의 캔들 데이터 다운로드 완료")

        # 2. 전략 데이터 준비
        print("📊 전략 데이터 준비 중...")
        df = strategy.prepare_data(df)
        print(f"✅ 데이터 준비 완료")

        # 3. 백테스팅 엔진 설정
        print("🔄 백테스팅 실행 중...")
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=commission,
        )

        # 4. 백테스팅 실행
        results = engine.run(
            df=df,
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
        )

        print("✅ 백테스팅 완료")

        # 5. 결과 출력
        print_results(results)

        return results

    except Exception as e:
        print(f"❌ 백테스팅 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_results(results):
    """백테스팅 결과를 콘솔에 출력"""

    if not results:
        return

    print("\n" + "-" * 100)
    print(f"📊 백테스팅 결과 요약")
    print("-" * 100)

    print(f"\n💰 수익 지표")
    print(f"  최종 자본금: ${results.get('final_capital', 0):,.2f}")
    total_return = results.get('total_return', 0)
    total_return_emoji = "🟢" if total_return > 0 else "🔴"
    print(f"  총 수익률: {total_return_emoji} {total_return:.2f}%")
    print(f"  최대 낙폭 (MDD): {results.get('max_drawdown', 0):.2f}%")
    print(f"  샤프 비율: {results.get('sharpe_ratio', 0):.2f}")

    print(f"\n📈 거래 통계")
    print(f"  총 거래 횟수: {results.get('total_trades', 0)}")
    print(f"  승리 거래: {results.get('winning_trades', 0)}")
    print(f"  패배 거래: {results.get('losing_trades', 0)}")
    print(f"  승률: {results.get('win_rate', 0):.2f}%")

    # 추가 지표
    if 'profit_factor' in results:
        print(f"\n📊 고급 지표")
        print(f"  Profit Factor: {results.get('profit_factor', 0):.2f}")
        print(f"  Sortino Ratio: {results.get('sortino_ratio', 0):.2f}")
        print(f"  Calmar Ratio: {results.get('calmar_ratio', 0):.2f}")

    print("\n" + "-" * 100)


def main():
    """메인 실행 함수"""

    print("\n" + "=" * 100)
    print("🎯 프로페셔널 전략 백테스팅 시스템")
    print("=" * 100)
    print()
    print("5개의 프로 전략을 순차적으로 백테스트합니다:")
    print("  1. ICT Smart Money Strategy")
    print("  2. Statistical Arbitrage Strategy")
    print("  3. Market Microstructure Strategy")
    print("  4. Adaptive Grid Trading Strategy")
    print("  5. Triangular Arbitrage Strategy")
    print()

    # 공통 설정
    symbol = 'BTCUSDT'
    initial_capital = 10000
    commission = 0.0004

    # 전략별 설정 및 실행
    strategies_config = [
        {
            'strategy': ICTSmartMoneyStrategy(symbol=symbol),
            'timeframe': '4h',
            'days': 365,
            'name': 'ICT Smart Money'
        },
        {
            'strategy': StatisticalArbitrageStrategy(symbol=symbol),
            'timeframe': '4h',
            'days': 365,
            'name': 'Statistical Arbitrage'
        },
        {
            'strategy': MarketMicrostructureStrategy(symbol=symbol),
            'timeframe': '1h',
            'days': 180,
            'name': 'Market Microstructure'
        },
        {
            'strategy': AdaptiveGridTradingStrategy(symbol=symbol),
            'timeframe': '1h',
            'days': 180,
            'name': 'Adaptive Grid Trading'
        },
        {
            'strategy': TriangularArbitrageStrategy(symbol=symbol),
            'timeframe': '15m',
            'days': 90,
            'name': 'Triangular Arbitrage'
        },
    ]

    results_summary = []

    for i, config in enumerate(strategies_config, 1):
        print(f"\n\n{'#' * 100}")
        print(f"#{' ' * 98}#")
        print(f"#  진행: [{i}/{len(strategies_config)}] {config['name']:<80}  #")
        print(f"#{' ' * 98}#")
        print(f"{'#' * 100}")

        start_time = time.time()

        result = run_single_backtest(
            strategy=config['strategy'],
            symbol=symbol,
            timeframe=config['timeframe'],
            days=config['days'],
            initial_capital=initial_capital,
            commission=commission
        )

        elapsed_time = time.time() - start_time

        if result:
            results_summary.append({
                'name': config['name'],
                'timeframe': config['timeframe'],
                'total_return': result.get('total_return', 0),
                'sharpe_ratio': result.get('sharpe_ratio', 0),
                'max_drawdown': result.get('max_drawdown', 0),
                'total_trades': result.get('total_trades', 0),
                'win_rate': result.get('win_rate', 0),
                'elapsed_time': elapsed_time
            })

        # 다음 백테스트 전 잠시 대기 (API rate limit)
        if i < len(strategies_config):
            print("\n⏳ 다음 백테스트 준비 중... (5초 대기)")
            time.sleep(5)

    # 최종 요약
    print("\n\n" + "=" * 100)
    print("🏆 전체 백테스트 결과 요약")
    print("=" * 100)
    print()

    if results_summary:
        print(f"{'전략':<35} {'타임프레임':<12} {'수익률':<12} {'샤프':<10} {'MDD':<10} {'거래수':<8} {'승률':<10} {'시간':<8}")
        print("-" * 100)

        for r in results_summary:
            return_emoji = "🟢" if r['total_return'] > 0 else "🔴"
            print(
                f"{r['name']:<35} {r['timeframe']:<12} "
                f"{return_emoji} {r['total_return']:>8.2f}%  "
                f"{r['sharpe_ratio']:>7.2f}   "
                f"{r['max_drawdown']:>7.2f}%  "
                f"{r['total_trades']:>6}  "
                f"{r['win_rate']:>7.2f}%  "
                f"{r['elapsed_time']:>5.1f}s"
            )

        print()

        # 베스트 전략
        best_sharpe = max(results_summary, key=lambda x: x['sharpe_ratio'])
        best_return = max(results_summary, key=lambda x: x['total_return'])

        print(f"\n🥇 최고 샤프 비율: {best_sharpe['name']} ({best_sharpe['sharpe_ratio']:.2f})")
        print(f"🥇 최고 수익률: {best_return['name']} ({best_return['total_return']:.2f}%)")

    print("\n" + "=" * 100)
    print("✨ 모든 백테스트 완료!")
    print("=" * 100)


if __name__ == "__main__":
    main()
