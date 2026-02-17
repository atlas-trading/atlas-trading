# Quick Usage Guide - Candlestick Chart

## 1-Minute Integration

### Add to PaperTrading.tsx

```tsx
import { ChartSection } from '../components/paper_trading';
import { useState, useEffect } from 'react';

// Add state
const [klineData, setKlineData] = useState([]);

// Fetch data when session loads
useEffect(() => {
  if (sessionData) {
    fetch(`https://api.binance.com/api/v3/klines?symbol=${sessionData.symbol}&interval=5m&limit=200`)
      .then(res => res.json())
      .then(data => {
        const formatted = data.map(k => ({
          time: k[0],
          open: parseFloat(k[1]),
          high: parseFloat(k[2]),
          low: parseFloat(k[3]),
          close: parseFloat(k[4]),
        }));
        setKlineData(formatted);
      });
  }
}, [sessionData]);

// Add component (place after stats grid, before positions table)
{sessionData && klineData.length > 0 && (
  <ChartSection
    klineData={klineData}
    trades={recentTrades}
    symbol={sessionData.symbol}
  />
)}
```

That's it! The chart will automatically:
- Display candlesticks with Binance dark theme
- Show buy/sell markers on trades
- Open detail panel when markers clicked
- Handle all interactions

## Component Files

```
src/components/
  charts/
    CandlestickChart.tsx    - Main chart component
    index.ts               - Exports
  paper_trading/
    TradeDetailPanel.tsx   - Trade details side panel
    ChartSection.tsx       - Integration wrapper
    index.ts              - Exports
```

## Props Reference

### ChartSection (Easiest)
```tsx
<ChartSection
  klineData={klineData}      // Array of candles
  trades={recentTrades}       // Array of trades
  symbol="BTCUSDT"           // Trading pair
/>
```

### CandlestickChart (Advanced)
```tsx
<CandlestickChart
  klineData={klineData}
  trades={trades}
  onTradeClick={(trade) => setSelectedTrade(trade)}
/>
```

### TradeDetailPanel (Manual)
```tsx
<TradeDetailPanel
  trade={selectedTrade}
  onClose={() => setSelectedTrade(null)}
/>
```

## Data Format

### Kline Data (from Binance)
```typescript
{
  time: 1708171200000,  // Timestamp in ms
  open: 51234.56,
  high: 51456.78,
  low: 51123.45,
  close: 51345.67
}
```

### Trade Data (from backend)
```typescript
{
  id: 123,
  symbol: "BTCUSDT",
  side: "buy",           // or "sell"
  entry_price: 51234.56,
  exit_price: 51456.78,  // null if open
  quantity: 0.1,
  pnl: 22.22,           // null if open
  pnl_percent: 0.43,    // null if open
  timestamp: "2024-02-17T12:00:00Z"
}
```

## Styling

All colors use CSS variables from `index.css`:

```css
--color-success: #0ECB81   /* Green for buy/profit/up */
--color-danger: #F6465D    /* Red for sell/loss/down */
--color-binance: #F0B90B   /* Yellow for accents */
--bg-primary: #0B0E11      /* Dark background */
```

## Common Issues

**Chart not showing?**
- Check klineData is not empty array
- Verify time values are in milliseconds
- Open browser console for errors

**Markers not appearing?**
- Ensure trades have non-null entry_price
- Check timestamp format is ISO 8601
- Verify trade times fall within kline range

**Panel not opening?**
- Check onTradeClick callback is provided
- Verify trade object has all required fields

## Full Documentation

See `CANDLESTICK_CHART_README.md` for complete documentation including:
- Advanced features
- Real-time updates with WebSocket
- Technical indicators
- Drawing tools
- Performance optimization
