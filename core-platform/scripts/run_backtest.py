"""백테스팅 실행 스크립트"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting import BacktestEngine, DataFetcher
from app.strategies import GoldenCrossStrategy
from app.strategies.golden_cross import create_strategy_function
from app.database import SessionLocal
from app.config import settings
from app.visualization import BacktestVisualizer


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(description="암호화폐 백테스팅 실행")

    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC/USDT",
        help="거래쌍 (예: BTC/USDT)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1d",
        choices=["1m", "5m", "15m", "1h", "4h", "1d", "1w"],
        help="타임프레임",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="백테스팅 기간 (일)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=settings.default_initial_capital,
        help="초기 자본금 (USDT)",
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=settings.default_commission,
        help="거래 수수료 (비율, 예: 0.001 = 0.1%%)",
    )
    parser.add_argument(
        "--fast-period",
        type=int,
        default=50,
        help="빠른 이동평균 기간",
    )
    parser.add_argument(
        "--slow-period",
        type=int,
        default=200,
        help="느린 이동평균 기간",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="데이터베이스에 저장하지 않음",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="결과 시각화 생성",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="시각화 결과 저장 디렉토리",
    )

    return parser.parse_args()


def print_results(results):
    """백테스팅 결과를 콘솔에 출력"""
    print("\n" + "=" * 80)
    print(f"📊 백테스팅 결과: {results['strategy_name']}")
    print("=" * 80)

    print(f"\n🎯 기본 정보")
    print(f"  거래쌍: {results['symbol']}")
    print(f"  타임프레임: {results['timeframe']}")
    print(f"  기간: {results['start_date'].strftime('%Y-%m-%d')} ~ {results['end_date'].strftime('%Y-%m-%d')}")
    print(f"  초기 자본금: ${results['initial_capital']:,.2f}")
    print(f"  수수료: {results['commission'] * 100:.2f}%")

    print(f"\n💰 수익 지표")
    print(f"  최종 자본금: ${results['final_capital']:,.2f}")
    total_return_emoji = "🟢" if results['total_return'] > 0 else "🔴"
    print(f"  총 수익률: {total_return_emoji} {results['total_return']:.2f}%")
    print(f"  최대 낙폭 (MDD): {results['max_drawdown']:.2f}%")
    print(f"  샤프 비율: {results['sharpe_ratio']:.2f}")

    print(f"\n📈 거래 통계")
    print(f"  총 거래 횟수: {results['total_trades']}")
    print(f"  승리 거래: {results['winning_trades']}")
    print(f"  패배 거래: {results['losing_trades']}")
    print(f"  승률: {results['win_rate']:.2f}%")

    if results['trades']:
        print(f"\n📋 최근 거래 (최대 5개)")
        print(f"  {'진입 시간':<20} {'청산 시간':<20} {'진입가':<12} {'청산가':<12} {'손익률':<10}")
        print(f"  {'-' * 74}")
        for trade in results['trades'][-5:]:
            entry_time = trade['entry_time'].strftime('%Y-%m-%d %H:%M')
            exit_time = trade['exit_time'].strftime('%Y-%m-%d %H:%M')
            pnl_emoji = "🟢" if trade['pnl_pct'] > 0 else "🔴"
            print(
                f"  {entry_time:<20} {exit_time:<20} "
                f"${trade['entry_price']:<11,.2f} ${trade['exit_price']:<11,.2f} "
                f"{pnl_emoji} {trade['pnl_pct']:>6.2f}%"
            )

    print("\n" + "=" * 80 + "\n")


def main():
    """메인 실행 함수"""
    args = parse_args()

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    print(f"🚀 백테스팅 시작")
    print(f"  거래쌍: {args.symbol}")
    print(f"  타임프레임: {args.timeframe}")
    print(f"  기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"  초기 자본금: ${args.capital:,.2f}")
    print()

    # 1. 데이터 다운로드
    print("📥 시장 데이터 다운로드 중...")
    fetcher = DataFetcher(exchange_id="binance")

    try:
        df = fetcher.fetch_ohlcv(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        print(f"❌ 데이터 다운로드 실패: {e}")
        sys.exit(1)

    if df.empty:
        print("❌ 데이터가 없습니다.")
        sys.exit(1)

    print(f"✅ {len(df)} 개의 캔들 데이터 다운로드 완료")

    # 2. 기술적 지표 계산
    print("📊 기술적 지표 계산 중...")
    df = fetcher.calculate_indicators(df)
    print(f"✅ 지표 계산 완료")

    # 3. 전략 설정
    print(f"⚙️  전략 설정: Golden Cross (MA {args.fast_period}/{args.slow_period})")
    strategy = GoldenCrossStrategy(
        fast_period=args.fast_period,
        slow_period=args.slow_period,
    )
    strategy_func = create_strategy_function(strategy)

    # 4. 백테스팅 실행
    print("🔄 백테스팅 실행 중...")
    engine = BacktestEngine(
        initial_capital=args.capital,
        commission=args.commission,
    )

    results = engine.run(
        df=df,
        strategy_func=strategy_func,
        strategy_name=strategy.name,
        symbol=args.symbol,
        timeframe=args.timeframe,
        parameters=strategy.get_parameters(),
    )

    print("✅ 백테스팅 완료")

    # 5. 결과 출력
    print_results(results)

    # 6. 데이터베이스 저장
    if not args.no_save:
        print("💾 결과를 데이터베이스에 저장 중...")
        try:
            db = SessionLocal()
            backtest_run = engine.save_to_db(db, results)
            print(f"✅ 저장 완료 (Run ID: {backtest_run.id})")
            db.close()
        except Exception as e:
            print(f"❌ 데이터베이스 저장 실패: {e}")
            if db:
                db.close()
    else:
        print("ℹ️  데이터베이스 저장 건너뜀 (--no-save)")

    # 7. 시각화
    if args.visualize:
        output_dir = Path(args.output_dir)
        visualizer = BacktestVisualizer(results, output_dir=str(output_dir))
        visualizer.generate_all_plots(save=True, show=False)
        visualizer.save_summary_report()

    print("\n✨ 백테스팅 완료!")


if __name__ == "__main__":
    main()
