"""다중 심볼 백테스팅 실행 스크립트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.utils.backtest_saver import save_backtest_to_db
from app.strategies.ict_smart_money import ICTSmartMoneyStrategy
from app.strategies.statistical_arbitrage import StatisticalArbitrageStrategy
from app.strategies.market_microstructure import MarketMicrostructureStrategy
from app.strategies.adaptive_grid_trading import AdaptiveGridTradingStrategy
from app.strategies.triangular_arbitrage import TriangularArbitrageStrategy


# 테스트할 심볼 및 설정 (펀더멘털 있는 코인만)
SYMBOLS_CONFIG = [
    {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'use_case': 'Digital Gold', 'volatility': 'medium'},
    {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'use_case': 'Smart Contracts', 'volatility': 'medium'},
    {'symbol': 'BNBUSDT', 'name': 'Binance Coin', 'use_case': 'Exchange Token', 'volatility': 'medium'},
    {'symbol': 'SOLUSDT', 'name': 'Solana', 'use_case': 'High-Performance L1', 'volatility': 'high'},
    {'symbol': 'ADAUSDT', 'name': 'Cardano', 'use_case': 'Academic Blockchain', 'volatility': 'high'},
    {'symbol': 'XRPUSDT', 'name': 'Ripple', 'use_case': 'Cross-Border Payment', 'volatility': 'high'},
    {'symbol': 'AVAXUSDT', 'name': 'Avalanche', 'use_case': 'DeFi Platform', 'volatility': 'high'},
    {'symbol': 'DOTUSDT', 'name': 'Polkadot', 'use_case': 'Interchain', 'volatility': 'high'},
    {'symbol': 'MATICUSDT', 'name': 'Polygon', 'use_case': 'Ethereum L2', 'volatility': 'high'},
    {'symbol': 'LINKUSDT', 'name': 'Chainlink', 'use_case': 'Oracle Network', 'volatility': 'high'},
    {'symbol': 'ATOMUSDT', 'name': 'Cosmos', 'use_case': 'Interchain Hub', 'volatility': 'high'},
]

# 전략별 설정
STRATEGIES_CONFIG = [
    {
        'name': 'ICT Smart Money',
        'class': ICTSmartMoneyStrategy,
        'timeframe': '1d',  # 길게 잡음
        'days': 730,  # 2년
    },
    {
        'name': 'Statistical Arbitrage',
        'class': StatisticalArbitrageStrategy,
        'timeframe': '1d',
        'days': 730,  # 2년
    },
    {
        'name': 'Market Microstructure',
        'class': MarketMicrostructureStrategy,
        'timeframe': '4h',
        'days': 365,  # 1년
    },
    {
        'name': 'Adaptive Grid Trading',
        'class': AdaptiveGridTradingStrategy,
        'timeframe': '4h',
        'days': 365,  # 1년
    },
    {
        'name': 'Triangular Arbitrage',
        'class': TriangularArbitrageStrategy,
        'timeframe': '1h',
        'days': 180,  # 6개월
    },
]


def run_backtest(strategy_class, symbol, timeframe, days, initial_capital=10000, commission=0.0004):
    """단일 백테스트 실행"""

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        # 1. 데이터 다운로드
        fetcher = DataFetcher(exchange_id="binance")
        df = fetcher.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty or len(df) < 100:
            return None

        # 2. 전략 초기화 및 데이터 준비
        strategy = strategy_class(symbol=symbol)
        df = strategy.prepare_data(df)

        # 3. 백테스팅 실행
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=commission,
        )

        results = engine.run(
            df=df,
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
        )

        return results

    except Exception as e:
        print(f"      ❌ 에러: {e}")
        return None


def main():
    """메인 실행 함수"""

    print("\n" + "=" * 120)
    print("🌍 다중 심볼 백테스팅 시스템")
    print("=" * 120)
    print()
    print(f"테스트 대상: {len(SYMBOLS_CONFIG)}개 심볼 × {len(STRATEGIES_CONFIG)}개 전략 = {len(SYMBOLS_CONFIG) * len(STRATEGIES_CONFIG)}개 백테스트")
    print()
    print("심볼 목록 (펀더멘털 기반):")
    for s in SYMBOLS_CONFIG:
        print(f"  - {s['symbol']:<12} ({s['name']:<15}) 유스케이스: {s['use_case']:<20} 변동성: {s['volatility']}")
    print()
    print("전략 목록:")
    for s in STRATEGIES_CONFIG:
        print(f"  - {s['name']:<30} {s['timeframe']:<6} {s['days']}일")
    print()

    # 결과 저장
    all_results = []

    # 전략별로 순회
    for strategy_idx, strategy_config in enumerate(STRATEGIES_CONFIG, 1):
        print(f"\n{'#' * 120}")
        print(f"# 전략 [{strategy_idx}/{len(STRATEGIES_CONFIG)}]: {strategy_config['name']:<80} #")
        print(f"{'#' * 120}\n")

        # 심볼별로 백테스트
        for symbol_idx, symbol_config in enumerate(SYMBOLS_CONFIG, 1):
            symbol = symbol_config['symbol']
            symbol_name = symbol_config['name']

            print(f"  [{symbol_idx}/{len(SYMBOLS_CONFIG)}] {symbol:<12} ({symbol_name:<15}) ", end='', flush=True)

            start_time = time.time()

            result = run_backtest(
                strategy_class=strategy_config['class'],
                symbol=symbol,
                timeframe=strategy_config['timeframe'],
                days=strategy_config['days'],
            )

            elapsed = time.time() - start_time

            if result and result.get('total_trades', 0) > 0:
                total_return = result.get('total_return', 0)
                sharpe = result.get('sharpe_ratio', 0)
                trades = result.get('total_trades', 0)
                win_rate = result.get('win_rate', 0)

                emoji = "🟢" if total_return > 0 else "🔴"
                print(f"{emoji} 수익률: {total_return:>7.2f}%  샤프: {sharpe:>5.2f}  거래: {trades:>4}개  승률: {win_rate:>5.1f}%  ({elapsed:.1f}s)")

                all_results.append({
                    'strategy': strategy_config['name'],
                    'symbol': symbol,
                    'symbol_name': symbol_name,
                    'timeframe': strategy_config['timeframe'],
                    'total_return': total_return,
                    'sharpe_ratio': sharpe,
                    'max_drawdown': result.get('max_drawdown', 0),
                    'total_trades': trades,
                    'win_rate': win_rate,
                    'elapsed_time': elapsed
                })

                # DB에 저장
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=strategy_config['days'])
                    save_backtest_to_db(
                        strategy_name=strategy_config['name'],
                        symbol=symbol,
                        timeframe=strategy_config['timeframe'],
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=10000,
                        commission=0.0004,
                        result=result,
                        parameters=None,
                    )
                except Exception as e:
                    print(f"      ⚠️  DB 저장 실패: {e}")
            elif result:
                print(f"⚪ 거래 없음 ({elapsed:.1f}s)")
            else:
                print(f"❌ 실패 ({elapsed:.1f}s)")

            # API rate limit 방지
            time.sleep(0.5)

        print()

    # 최종 요약
    print("\n" + "=" * 120)
    print("🏆 전체 백테스트 결과 요약")
    print("=" * 120)
    print()

    if all_results:
        # DataFrame으로 변환
        df_results = pd.DataFrame(all_results)

        # 수익난 결과만 필터링
        profitable = df_results[df_results['total_return'] > 0].sort_values('total_return', ascending=False)

        if len(profitable) > 0:
            print("✅ 수익 발생 전략 (Top 20):\n")
            print(f"{'전략':<30} {'심볼':<12} {'타임프레임':<10} {'수익률':<12} {'샤프':<10} {'MDD':<10} {'거래수':<8} {'승률':<10}")
            print("-" * 120)

            for idx, row in profitable.head(20).iterrows():
                return_emoji = "🟢" if row['total_return'] > 5 else "🔵"
                print(
                    f"{row['strategy']:<30} {row['symbol']:<12} {row['timeframe']:<10} "
                    f"{return_emoji} {row['total_return']:>8.2f}%  "
                    f"{row['sharpe_ratio']:>7.2f}   "
                    f"{row['max_drawdown']:>7.2f}%  "
                    f"{row['total_trades']:>6}  "
                    f"{row['win_rate']:>7.2f}%"
                )

            print()

            # 전략별 통계
            print("\n📊 전략별 평균 성과:\n")
            strategy_stats = df_results.groupby('strategy').agg({
                'total_return': 'mean',
                'sharpe_ratio': 'mean',
                'total_trades': 'sum',
                'win_rate': 'mean'
            }).sort_values('total_return', ascending=False)

            print(f"{'전략':<30} {'평균 수익률':<15} {'평균 샤프':<12} {'총 거래수':<12} {'평균 승률'}")
            print("-" * 120)
            for strategy, stats in strategy_stats.iterrows():
                emoji = "🟢" if stats['total_return'] > 0 else "🔴"
                print(
                    f"{strategy:<30} {emoji} {stats['total_return']:>10.2f}%  "
                    f"{stats['sharpe_ratio']:>9.2f}   "
                    f"{int(stats['total_trades']):>10}  "
                    f"{stats['win_rate']:>9.2f}%"
                )

            print()

            # 심볼별 통계
            print("\n🪙 심볼별 평균 성과:\n")
            symbol_stats = df_results.groupby('symbol').agg({
                'total_return': 'mean',
                'sharpe_ratio': 'mean',
                'total_trades': 'sum',
                'win_rate': 'mean'
            }).sort_values('total_return', ascending=False)

            print(f"{'심볼':<12} {'평균 수익률':<15} {'평균 샤프':<12} {'총 거래수':<12} {'평균 승률'}")
            print("-" * 120)
            for symbol, stats in symbol_stats.iterrows():
                emoji = "🟢" if stats['total_return'] > 0 else "🔴"
                print(
                    f"{symbol:<12} {emoji} {stats['total_return']:>10.2f}%  "
                    f"{stats['sharpe_ratio']:>9.2f}   "
                    f"{int(stats['total_trades']):>10}  "
                    f"{stats['win_rate']:>9.2f}%"
                )

            print()

            # 최고 성과
            best = profitable.iloc[0]
            print(f"\n🥇 최고 성과:")
            print(f"   전략: {best['strategy']}")
            print(f"   심볼: {best['symbol']} ({best['symbol_name']})")
            print(f"   타임프레임: {best['timeframe']}")
            print(f"   수익률: {best['total_return']:.2f}%")
            print(f"   샤프 비율: {best['sharpe_ratio']:.2f}")
            print(f"   거래 횟수: {int(best['total_trades'])}개")
            print(f"   승률: {best['win_rate']:.2f}%")

        else:
            print("❌ 수익을 낸 전략이 없습니다.")

        # 결과를 CSV로 저장
        output_file = Path(__file__).parent.parent / 'results' / f'multi_symbol_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        output_file.parent.mkdir(exist_ok=True)
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 결과 저장: {output_file}")

    else:
        print("❌ 백테스트 결과가 없습니다.")

    print("\n" + "=" * 120)
    print("✨ 모든 백테스트 완료!")
    print("=" * 120)


if __name__ == "__main__":
    main()
