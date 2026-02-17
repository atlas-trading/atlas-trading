"""ICT Smart Money 전략 낮은 타임프레임 테스트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.strategies.ict_smart_money import ICTSmartMoneyStrategy


# 테스트할 심볼 (상위 5개)
TEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']

# 테스트할 타임프레임 및 파라미터
TIMEFRAME_CONFIGS = [
    {
        'timeframe': '4h',
        'days': 365,
        'params': [
            {'swing_lookback': 5, 'fvg_min_size': 0.001, 'liquidity_raid_tolerance': 0.005},
            {'swing_lookback': 7, 'fvg_min_size': 0.0015, 'liquidity_raid_tolerance': 0.003},
            {'swing_lookback': 10, 'fvg_min_size': 0.002, 'liquidity_raid_tolerance': 0.004},
        ]
    },
    {
        'timeframe': '1h',
        'days': 180,
        'params': [
            {'swing_lookback': 5, 'fvg_min_size': 0.0008, 'liquidity_raid_tolerance': 0.006},
            {'swing_lookback': 7, 'fvg_min_size': 0.001, 'liquidity_raid_tolerance': 0.004},
            {'swing_lookback': 10, 'fvg_min_size': 0.0015, 'liquidity_raid_tolerance': 0.003},
        ]
    },
    {
        'timeframe': '15m',
        'days': 90,
        'params': [
            {'swing_lookback': 5, 'fvg_min_size': 0.0005, 'liquidity_raid_tolerance': 0.008},
            {'swing_lookback': 7, 'fvg_min_size': 0.0008, 'liquidity_raid_tolerance': 0.006},
        ]
    },
]


def test_ict_timeframe(symbol, timeframe, days, params):
    """특정 타임프레임에서 ICT 전략 테스트"""

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        # 데이터 다운로드
        fetcher = DataFetcher(exchange_id="binance")
        df = fetcher.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty or len(df) < 100:
            return None

        # 전략 실행
        strategy = ICTSmartMoneyStrategy(symbol=symbol, **params)
        df = strategy.prepare_data(df)

        engine = BacktestEngine(initial_capital=10000, commission=0.0004)
        result = engine.run(df=df, strategy=strategy, symbol=symbol, timeframe=timeframe)

        return result

    except Exception as e:
        print(f"      ❌ 에러: {e}")
        return None


def main():
    """메인 실행"""

    print("\n" + "=" * 120)
    print("🔍 ICT Smart Money - 낮은 타임프레임 테스트")
    print("=" * 120)
    print(f"\n테스트 심볼: {', '.join(TEST_SYMBOLS)}")
    print(f"타임프레임: 4h, 1h, 15m\n")

    all_results = []

    for tf_config in TIMEFRAME_CONFIGS:
        timeframe = tf_config['timeframe']
        days = tf_config['days']

        print(f"\n{'#' * 120}")
        print(f"# 타임프레임: {timeframe} ({days}일)")
        print(f"{'#' * 120}\n")

        for param_idx, params in enumerate(tf_config['params'], 1):
            print(f"\n파라미터 세트 {param_idx}/{len(tf_config['params'])}: "
                  f"swing={params['swing_lookback']}, "
                  f"fvg={params['fvg_min_size']}, "
                  f"raid={params['liquidity_raid_tolerance']}\n")

            for symbol in TEST_SYMBOLS:
                print(f"  {symbol:<12} ", end='', flush=True)

                start_time = time.time()
                result = test_ict_timeframe(symbol, timeframe, days, params)
                elapsed = time.time() - start_time

                if result and result.get('total_trades', 0) > 0:
                    total_return = result['total_return']
                    trades = result['total_trades']
                    win_rate = result['win_rate']
                    sharpe = result.get('sharpe_ratio', 0)

                    emoji = "🟢" if total_return > 0 else "🔴"
                    print(f"{emoji} 수익률: {total_return:>7.2f}%  거래: {trades:>3}개  승률: {win_rate:>5.1f}%  샤프: {sharpe:>5.2f}  ({elapsed:.1f}s)")

                    all_results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'params': params,
                        'total_return': total_return,
                        'total_trades': trades,
                        'win_rate': win_rate,
                        'sharpe_ratio': sharpe,
                    })
                else:
                    print(f"⚪ 거래 없음 ({elapsed:.1f}s)")

                time.sleep(0.3)

    # 결과 요약
    print("\n" + "=" * 120)
    print("📊 ICT Smart Money 낮은 타임프레임 테스트 결과")
    print("=" * 120)

    if all_results:
        # 수익난 결과만
        profitable = [r for r in all_results if r['total_return'] > 0]

        if profitable:
            print(f"\n✅ 수익 발생: {len(profitable)}개\n")

            # 수익률 순 정렬
            profitable.sort(key=lambda x: x['total_return'], reverse=True)

            print(f"{'심볼':<12} {'타임프레임':<10} {'수익률':<12} {'거래수':<8} {'승률':<8} {'샤프':<8} {'파라미터'}")
            print("-" * 120)

            for r in profitable[:20]:  # Top 20
                print(
                    f"{r['symbol']:<12} {r['timeframe']:<10} "
                    f"{r['total_return']:>8.2f}%  {r['total_trades']:>6}  "
                    f"{r['win_rate']:>6.1f}%  {r['sharpe_ratio']:>6.2f}  "
                    f"swing={r['params']['swing_lookback']}, "
                    f"fvg={r['params']['fvg_min_size']}, "
                    f"raid={r['params']['liquidity_raid_tolerance']}"
                )

            print()

            # 타임프레임별 통계
            print("\n📈 타임프레임별 평균 성과:\n")
            timeframes = {}
            for r in all_results:
                tf = r['timeframe']
                if tf not in timeframes:
                    timeframes[tf] = {'returns': [], 'trades': [], 'win_rates': []}
                timeframes[tf]['returns'].append(r['total_return'])
                timeframes[tf]['trades'].append(r['total_trades'])
                timeframes[tf]['win_rates'].append(r['win_rate'])

            for tf, stats in sorted(timeframes.items()):
                avg_return = sum(stats['returns']) / len(stats['returns'])
                avg_trades = sum(stats['trades']) / len(stats['trades'])
                avg_win_rate = sum(stats['win_rates']) / len(stats['win_rates'])

                emoji = "🟢" if avg_return > 0 else "🔴"
                print(f"  {tf:<8} {emoji} 평균 수익률: {avg_return:>7.2f}%  "
                      f"평균 거래: {avg_trades:>5.1f}개  평균 승률: {avg_win_rate:>5.1f}%")
        else:
            print("\n⚠️  수익 발생한 결과 없음")
    else:
        print("\n⚠️  모든 타임프레임에서 거래 없음")
        print("ICT 전략은 일중 타임프레임에서도 조건이 너무 엄격할 수 있습니다.")

    print("\n" + "=" * 120)
    print("✨ 테스트 완료!")
    print("=" * 120)


if __name__ == "__main__":
    main()
