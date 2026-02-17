import { useState } from 'react';
import CandlestickChart from '../charts/CandlestickChart';
import TradeDetailPanel from './TradeDetailPanel';
import Card from '../common/Card';
import type { PaperTradingTrade } from '../../types/paper_trading';

interface KlineData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface ChartSectionProps {
  klineData: KlineData[];
  trades: PaperTradingTrade[];
  symbol: string;
}

export default function ChartSection({ klineData, trades, symbol }: ChartSectionProps) {
  const [selectedTrade, setSelectedTrade] = useState<PaperTradingTrade | null>(null);

  return (
    <>
      <Card style={{ marginBottom: '20px' }}>
        <div style={{ padding: '20px 24px 12px', borderBottom: '1px solid var(--border-primary)' }}>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {symbol} Price Chart
          </h2>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-tertiary)' }}>
            Click on trade markers to view details
          </p>
        </div>
        <div style={{ padding: '24px' }}>
          <CandlestickChart
            klineData={klineData}
            trades={trades}
            onTradeClick={setSelectedTrade}
          />
        </div>
      </Card>

      {/* Trade Detail Side Panel */}
      <TradeDetailPanel trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </>
  );
}
