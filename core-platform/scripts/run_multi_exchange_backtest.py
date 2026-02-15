"""
여러 거래소에서 동일한 전략을 백테스트하고 비교

바이낸스, 바이비트, OKX 등 여러 거래소의 데이터로 동시에 백테스트를 실행하여
거래소별 차이를 비교합니다.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import pandas as pd
import ccxt
from app.backtesting.engine import BacktestEngine
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity
from app.database import SessionLocal


def fetch_exchange_data(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """Fetch historical data from any supported exchange"""
    try:
        exchange_class = getattr(ccxt, exchange_name.lower())
        exchange = exchange_class()

        since = int(start_date.timestamp() * 1000)
        end = int(end_date.timestamp() * 1000)

        all_ohlcv = []
        current = since

        print(f"  Fetching from {exchange_name.upper()}...", end=" ")

        while current < end:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current, limit=1000)
                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                current = ohlcv[-1][0] + 1

                if ohlcv[-1][0] >= end:
                    break

            except Exception as e:
                print(f"Error: {e}")
                return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

        print(f"✓ {len(df)} candles")
        return df

    except Exception as e:
        print(f"✗ Failed: {e}")
        return pd.DataFrame()


def run_backtest_on_exchange(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    commission: float,
    strategy_name: str,
) -> dict:
    """단일 거래소에서 백테스트 실행"""

    # Fetch data
    df = fetch_exchange_data(exchange_name, symbol, timeframe, start_date, end_date)

    if df.empty:
        return None

    # Create strategy
    strategy = RSIMeanReversionStrategy(
        rsi_period=14,
        oversold_threshold=30,
        overbought_threshold=70,
    )

    # Create engine with Kelly sizing
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=commission,
        use_kelly_sizing=True,
        kelly_window=20,
        kelly_fraction=0.5,
    )

    # Run backtest
    result = engine.run(
        df=df,
        strategy=strategy,
        strategy_name=f"{strategy_name}_{exchange_name.upper()}",
        symbol=symbol,
        timeframe=timeframe,
    )

    return result


def main():
    print("=" * 80)
    print("MULTI-EXCHANGE BACKTEST COMPARISON")
    print("=" * 80)

    # Parameters
    exchanges = ['binance', 'bybit']  # Add more: 'okx', 'bingx', 'bitget'
    symbol = 'BTC/USDT'
    timeframe = '1d'
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 2, 14)
    initial_capital = 10000.0
    commission = 0.001
    strategy_name = 'RSI_Mean_Reversion_14_30_70'

    print(f"\n{'Strategy:':<20} {strategy_name}")
    print(f"{'Symbol:':<20} {symbol}")
    print(f"{'Timeframe:':<20} {timeframe}")
    print(f"{'Period:':<20} {start_date.date()} to {end_date.date()}")
    print(f"{'Initial Capital:':<20} ${initial_capital:,.2f}")
    print(f"{'Commission:':<20} {commission * 100:.3f}%")
    print(f"{'Exchanges:':<20} {', '.join([e.upper() for e in exchanges])}")

    print("\n" + "=" * 80)
    print("FETCHING DATA")
    print("=" * 80)

    # Run backtests
    results = {}
    for exchange in exchanges:
        print(f"\n{exchange.upper()}:")
        result = run_backtest_on_exchange(
            exchange, symbol, timeframe, start_date, end_date,
            initial_capital, commission, strategy_name
        )
        if result:
            results[exchange] = result

    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    if not results:
        print("No successful backtests.")
        return

    # Header
    header = f"{'Exchange':<12} {'Final $':<12} {'Return %':<12} {'Trades':<10} {'Win Rate':<12} {'Max DD':<12} {'Sharpe':<10}"
    print(header)
    print("-" * 80)

    # Results
    for exchange, result in results.items():
        print(
            f"{exchange.upper():<12} "
            f"${result['final_capital']:>10,.2f} "
            f"{result['total_return']:>10.2f}% "
            f"{result['total_trades']:>8} "
            f"{result['win_rate']:>10.2f}% "
            f"{result['max_drawdown']:>10.2f}% "
            f"{result['sharpe_ratio']:>8.3f}"
        )

    # Best performer
    print("\n" + "-" * 80)
    best_exchange = max(results.items(), key=lambda x: x[1]['total_return'])
    print(f"Best Performer: {best_exchange[0].upper()} ({best_exchange[1]['total_return']:+.2f}%)")

    # Save to database
    print("\n" + "=" * 80)
    print("SAVING TO DATABASE")
    print("=" * 80)

    db = SessionLocal()
    try:
        for exchange, result in results.items():
            # Create backtest run
            backtest = BacktestRun(
                strategy_name=result['strategy_name'],
                symbol=result['symbol'],
                timeframe=result.get('timeframe', '1d'),
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=result['final_capital'],
                total_return=result['total_return'],
                max_drawdown=result['max_drawdown'],
                sharpe_ratio=result.get('sharpe_ratio', 0),
                total_trades=result['total_trades'],
                winning_trades=result.get('winning_trades', 0),
                losing_trades=result.get('losing_trades', 0),
                win_rate=result.get('win_rate', 0),
                commission=commission,
            )
            db.add(backtest)
            db.flush()

            # Save trades
            for trade in result.get('trades', []):
                db_trade = BacktestTrade(
                    backtest_run_id=backtest.id,
                    entry_time=trade['entry_time'],
                    exit_time=trade['exit_time'],
                    side=trade['side'],
                    entry_price=trade['entry_price'],
                    exit_price=trade['exit_price'],
                    quantity=trade['quantity'],
                    pnl=trade['pnl'],
                    pnl_pct=trade.get('pnl_pct', 0),
                    commission_paid=trade.get('commission', 0),
                    position_size_pct=trade.get('position_size_pct', 1.0),
                )
                db.add(db_trade)

            # Save equity curve
            for point in result.get('equity_curve', []):
                db_point = BacktestEquity(
                    backtest_run_id=backtest.id,
                    timestamp=point['timestamp'],
                    equity=point['equity'],
                    cash=point.get('cash', initial_capital),
                    position_value=point.get('position_value', 0),
                )
                db.add(db_point)

            print(f"✓ Saved {exchange.upper()} backtest (ID: {backtest.id})")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"✗ Error saving to database: {e}")
        raise
    finally:
        db.close()

    print("\n" + "=" * 80)
    print("COMPLETED")
    print("=" * 80)


if __name__ == '__main__':
    main()
