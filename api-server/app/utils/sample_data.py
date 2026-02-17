"""
Sample data generator for backtesting
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_ohlcv(
    symbol: str = "BTCUSDT",
    start_date: datetime = None,
    end_date: datetime = None,
    initial_price: float = 50000.0,
    volatility: float = 0.02,
    trend: float = 0.0001
) -> pd.DataFrame:
    """
    Generate sample OHLCV data for backtesting

    Args:
        symbol: Trading symbol
        start_date: Start date (default: 1 year ago)
        end_date: End date (default: today)
        initial_price: Starting price
        volatility: Daily volatility (default: 2%)
        trend: Daily trend (default: 0.01% up)

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    if end_date is None:
        end_date = datetime.now()

    # Generate daily timestamps
    dates = pd.date_range(start=start_date, end=end_date, freq='1D')
    n = len(dates)

    # Generate random returns with trend
    np.random.seed(42)  # For reproducibility
    returns = np.random.normal(trend, volatility, n)

    # Calculate prices from returns
    price_multipliers = np.exp(np.cumsum(returns))
    close_prices = initial_price * price_multipliers

    # Generate OHLC from close prices
    data = []
    for i, (date, close) in enumerate(zip(dates, close_prices)):
        # Generate intraday variation
        daily_range = close * volatility * np.random.uniform(0.5, 1.5)

        # Open close to previous close (with small gap)
        if i == 0:
            open_price = initial_price
        else:
            gap = np.random.normal(0, volatility / 4)
            open_price = close_prices[i-1] * (1 + gap)

        # High/Low based on open and close
        high = max(open_price, close) + daily_range * np.random.uniform(0, 0.5)
        low = min(open_price, close) - daily_range * np.random.uniform(0, 0.5)

        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Generate volume (with some correlation to price movement)
        base_volume = 1000000
        volume_multiplier = 1 + abs(returns[i]) * 10
        volume = base_volume * volume_multiplier * np.random.uniform(0.8, 1.2)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    return df


def generate_trending_ohlcv(
    symbol: str = "BTCUSDT",
    start_date: datetime = None,
    end_date: datetime = None,
    initial_price: float = 50000.0
) -> pd.DataFrame:
    """Generate uptrending market data (good for trend-following strategies)"""
    return generate_sample_ohlcv(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_price=initial_price,
        volatility=0.015,
        trend=0.0005  # Strong uptrend
    )


def generate_ranging_ohlcv(
    symbol: str = "BTCUSDT",
    start_date: datetime = None,
    end_date: datetime = None,
    initial_price: float = 50000.0
) -> pd.DataFrame:
    """Generate ranging market data (good for mean-reversion strategies)"""
    return generate_sample_ohlcv(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_price=initial_price,
        volatility=0.025,
        trend=0.0  # No trend, just ranging
    )


def generate_volatile_ohlcv(
    symbol: str = "BTCUSDT",
    start_date: datetime = None,
    end_date: datetime = None,
    initial_price: float = 50000.0
) -> pd.DataFrame:
    """Generate high volatility market data (good for breakout strategies)"""
    return generate_sample_ohlcv(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_price=initial_price,
        volatility=0.035,
        trend=0.0002
    )
