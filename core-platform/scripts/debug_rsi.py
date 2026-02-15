"""Debug RSI strategy"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import pandas as pd
import ccxt
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy

# Fetch small sample
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=100)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

print("Raw data shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())

# Create strategy and prepare data
strategy = RSIMeanReversionStrategy(rsi_period=14, oversold_threshold=30, overbought_threshold=70)
df = strategy.prepare_data(df)

print("\nAfter adding RSI:")
print(df[['timestamp', 'close', 'rsi_14']].tail(20))

print("\nRSI Statistics:")
print(df['rsi_14'].describe())

print("\nRSI < 30 count:", (df['rsi_14'] < 30).sum())
print("RSI > 70 count:", (df['rsi_14'] > 70).sum())

# Test strategy signals
print("\n" + "="*60)
print("Testing strategy signals...")
print("="*60)

signals = []
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        signals.append({
            'timestamp': row['timestamp'],
            'close': row['close'],
            'rsi': row['rsi_14'],
            'signal': signal,
            'position': strategy.has_position
        })
        print(f"{row['timestamp']:%Y-%m-%d} | Price: ${row['close']:,.0f} | RSI: {row['rsi_14']:.1f} | Signal: {signal} | Has Position: {strategy.has_position}")

print(f"\nTotal signals generated: {len(signals)}")
