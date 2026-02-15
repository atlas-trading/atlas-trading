"""
RSI Mean Reversion 전략 백테스트 실행 스크립트
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
    """
    Fetch historical data from any supported exchange

    Supported exchanges: binance, bybit, okx, bingx, bitget, etc.
    """
    # Create exchange instance
    exchange_class = getattr(ccxt, exchange_name.lower())
    exchange = exchange_class()

    # Convert dates to milliseconds
    since = int(start_date.timestamp() * 1000)
    end = int(end_date.timestamp() * 1000)

    all_ohlcv = []
    current = since

    print(f"Fetching {symbol} {timeframe} data from {exchange_name.upper()} ({start_date.date()} to {end_date.date()})...")

    while current < end:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current, limit=1000)
            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)
            current = ohlcv[-1][0] + 1

            # Stop if we've reached the end date
            if ohlcv[-1][0] >= end:
                break

        except Exception as e:
            print(f"Error fetching data from {exchange_name}: {e}")
            break

    # Convert to DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

    print(f"✓ Fetched {len(df)} candles from {exchange_name.upper()}")
    return df


def main():
    print("=" * 60)
    print("RSI Mean Reversion Strategy Backtest")
    print("=" * 60)

    # Parameters
    exchange = 'binance'  # Change to: 'bybit', 'okx', 'bingx', etc.
    symbol = 'BTC/USDT'
    timeframe = '1d'
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 2, 14)
    initial_capital = 10000.0
    commission = 0.001
    strategy_name = 'RSI_Mean_Reversion_14_30_70'

    print(f"\n{'Exchange:':<20} {exchange.upper()}")
    print(f"{'Strategy:':<20} {strategy_name}")
    print(f"{'Symbol:':<20} {symbol}")
    print(f"{'Timeframe:':<20} {timeframe}")
    print(f"{'Period:':<20} {start_date.date()} to {end_date.date()}")
    print(f"{'Initial Capital:':<20} ${initial_capital:,.2f}")
    print(f"{'Commission Rate:':<20} {commission * 100:.3f}%")

    print("\n" + "-" * 60)

    # Fetch data
    df = fetch_exchange_data(exchange, symbol, timeframe, start_date, end_date)

    if df.empty:
        print("✗ No data fetched. Exiting.")
        return

    # Create strategy
    strategy = RSIMeanReversionStrategy(
        rsi_period=14,
        oversold_threshold=30,
        overbought_threshold=70,
    )

    # Create backtest engine with Kelly sizing
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=commission,
        use_kelly_sizing=True,
        kelly_window=20,
        kelly_fraction=0.5,  # Half Kelly
    )

    print("Running backtest...")
    print("-" * 60)

    # Run backtest
    result = engine.run(
        df=df,
        strategy=strategy,
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
    )

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"{'Total Trades:':<25} {result.get('total_trades', 0)}")
    print(f"{'Winning Trades:':<25} {result.get('winning_trades', 0)}")
    print(f"{'Losing Trades:':<25} {result.get('losing_trades', 0)}")
    print(f"{'Win Rate:':<25} {result.get('win_rate', 0):.2f}%")
    print()
    print(f"{'Final Capital:':<25} ${result.get('final_capital', 0):,.2f}")
    print(f"{'Total Return:':<25} {result.get('total_return', 0):+.2f}%")
    print(f"{'Max Drawdown:':<25} {result.get('max_drawdown', 0):.2f}%")
    print(f"{'Sharpe Ratio:':<25} {result.get('sharpe_ratio', 0):.3f}")
    print()
    print(f"{'Avg Win:':<25} ${result.get('avg_win', 0):.2f}")
    print(f"{'Avg Loss:':<25} ${result.get('avg_loss', 0):.2f}")
    print(f"{'Profit Factor:':<25} {result.get('profit_factor', 0):.3f}")
    print("=" * 60)

    # Save to database
    print("\nSaving to database...")
    db = SessionLocal()
    try:
        # Create backtest run record
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

        db.commit()
        print(f"✓ Saved backtest with ID: {backtest.id}")
        print(f"✓ Saved {len(result.get('trades', []))} trades")
        print(f"✓ Saved {len(result.get('equity_curve', []))} equity points")

    except Exception as e:
        db.rollback()
        print(f"✗ Error saving to database: {e}")
        raise
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Backtest completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
