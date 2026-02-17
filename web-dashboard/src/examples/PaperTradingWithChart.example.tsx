/**
 * Example: Paper Trading Page with Candlestick Chart Integration
 *
 * This demonstrates how to integrate the CandlestickChart component
 * into the Paper Trading page with real-time market data.
 *
 * Usage:
 * 1. Add this to your PaperTrading.tsx page
 * 2. Fetch kline data from Binance API or your backend
 * 3. Pass trades and kline data to ChartSection component
 */

import { useState, useEffect } from 'react';
import { ChartSection } from '../components/paper_trading';
import type { PaperTradingTrade } from '../types/paper_trading';

interface KlineData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export default function PaperTradingWithChartExample() {
  const [klineData, setKlineData] = useState<KlineData[]>([]);
  const [trades, setTrades] = useState<PaperTradingTrade[]>([]);
  const [loading, setLoading] = useState(true);

  // Example: Fetch kline data from Binance API
  const fetchKlineData = async (symbol: string, interval: string = '5m', limit: number = 200) => {
    try {
      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`
      );
      const data = await response.json();

      const formattedData: KlineData[] = data.map((kline: any) => ({
        time: kline[0], // Open time (milliseconds)
        open: parseFloat(kline[1]),
        high: parseFloat(kline[2]),
        low: parseFloat(kline[3]),
        close: parseFloat(kline[4]),
      }));

      return formattedData;
    } catch (error) {
      console.error('Failed to fetch kline data:', error);
      return [];
    }
  };

  // Example: Load data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);

      // Fetch kline data (replace BTCUSDT with actual symbol from session)
      const klines = await fetchKlineData('BTCUSDT', '5m', 200);
      setKlineData(klines);

      // Fetch trades from your backend (example)
      // const tradesResponse = await apiClient.get(`/paper-trading/sessions/${sessionId}/trades`);
      // setTrades(tradesResponse.data);

      setLoading(false);
    };

    loadData();
  }, []);

  if (loading) {
    return <div>Loading chart...</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Paper Trading with Candlestick Chart</h1>

      {/* Integrate Chart Section */}
      <ChartSection
        klineData={klineData}
        trades={trades}
        symbol="BTCUSDT"
      />

      {/* Rest of your Paper Trading UI */}
    </div>
  );
}

/**
 * Integration Steps for PaperTrading.tsx:
 *
 * 1. Import ChartSection:
 *    import { ChartSection } from '../components/paper_trading';
 *
 * 2. Add state for kline data:
 *    const [klineData, setKlineData] = useState<KlineData[]>([]);
 *
 * 3. Fetch kline data when session is loaded:
 *    useEffect(() => {
 *      if (sessionData) {
 *        fetchKlineData(sessionData.symbol).then(setKlineData);
 *      }
 *    }, [sessionData]);
 *
 * 4. Add ChartSection to render:
 *    <ChartSection
 *      klineData={klineData}
 *      trades={recentTrades}
 *      symbol={sessionData.symbol}
 *    />
 *
 * 5. Backend Integration (Optional):
 *    If you want to serve kline data from your backend instead of Binance directly:
 *
 *    - Add endpoint: GET /paper-trading/sessions/{session_id}/klines
 *    - Return format: Array<{time: number, open: number, high: number, low: number, close: number}>
 *    - Cache data to reduce Binance API calls
 */

/**
 * Advanced Features to Add:
 *
 * 1. Timeframe Selector:
 *    - Add buttons to switch between 1m, 5m, 15m, 1h, 4h, 1d
 *    - Reload kline data when timeframe changes
 *
 * 2. Real-time Updates:
 *    - Use WebSocket to stream live candles
 *    - Update last candle in real-time
 *
 * 3. Technical Indicators:
 *    - Add EMA/SMA lines to chart
 *    - Show RSI/MACD in separate panes
 *
 * 4. Trade Annotations:
 *    - Draw lines from entry to exit
 *    - Show stop loss / take profit levels
 *    - Highlight winning vs losing trades
 *
 * 5. Chart Export:
 *    - Screenshot functionality
 *    - Export to PNG/SVG
 */
