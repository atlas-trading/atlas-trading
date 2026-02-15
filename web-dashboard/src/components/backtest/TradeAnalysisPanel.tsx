// Trade analysis panel with charts
import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { backtestAPI } from '../../services/api';
import type { TradeAnalysis } from '../../types/backtest';
import Card from '../common/Card';
import LoadingSpinner from '../common/LoadingSpinner';

interface TradeAnalysisPanelProps {
  backtestId: number;
}

export default function TradeAnalysisPanel({ backtestId }: TradeAnalysisPanelProps) {
  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalysis();
  }, [backtestId]);

  const loadAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await backtestAPI.getTradeAnalysis(backtestId);
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trade analysis.');
      console.error('Failed to load trade analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error || !analysis) {
    return (
      <Card>
        <p style={{ color: 'var(--color-danger)', textAlign: 'center' }}>
          {error || 'Unable to load data.'}
        </p>
      </Card>
    );
  }

  // Win/Loss distribution chart data
  const distributionData = [
    { name: 'Small Win', count: analysis.small_wins_count, color: 'rgba(14, 203, 129, 0.6)' },
    { name: 'Medium Win', count: analysis.medium_wins_count, color: 'rgba(14, 203, 129, 0.8)' },
    { name: 'Large Win', count: analysis.large_wins_count, color: 'var(--color-success)' },
    { name: 'Small Loss', count: analysis.small_losses_count, color: 'rgba(246, 70, 93, 0.6)' },
    { name: 'Medium Loss', count: analysis.medium_losses_count, color: 'rgba(246, 70, 93, 0.8)' },
    { name: 'Large Loss', count: analysis.large_losses_count, color: 'var(--color-danger)' },
  ];

  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div>
      {/* Holding Period Analysis */}
      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Holding Period Analysis</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          <MetricItem label="Average Holding Time" value={`${formatNumber(analysis.avg_holding_hours, 1)}h`} />
          <MetricItem label="Median Holding Time" value={`${formatNumber(analysis.median_holding_hours, 1)}h`} />
          <MetricItem label="Min Holding Time" value={`${formatNumber(analysis.min_holding_hours, 1)}h`} />
          <MetricItem label="Max Holding Time" value={`${formatNumber(analysis.max_holding_hours, 1)}h`} />
        </div>
      </Card>

      {/* PnL Distribution */}
      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>PnL Distribution</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '30px' }}>
          <MetricItem label="Average PnL" value={formatCurrency(analysis.avg_pnl)} valueColor={analysis.avg_pnl >= 0 ? 'var(--color-success)' : 'var(--color-danger)'} />
          <MetricItem label="Median PnL" value={formatCurrency(analysis.median_pnl)} valueColor={analysis.median_pnl >= 0 ? 'var(--color-success)' : 'var(--color-danger)'} />
          <MetricItem label="Largest Win" value={formatCurrency(analysis.largest_win)} valueColor="var(--color-success)" />
          <MetricItem label="Largest Loss" value={formatCurrency(analysis.largest_loss)} valueColor="var(--color-danger)" />
          <MetricItem label="Average Win Size" value={formatCurrency(analysis.avg_win)} valueColor="var(--color-success)" />
          <MetricItem label="Average Loss Size" value={formatCurrency(analysis.avg_loss)} valueColor="var(--color-danger)" />
        </div>

        {/* Win/Loss Distribution Chart */}
        <h4 style={{ marginBottom: '15px', fontSize: '14px', color: 'var(--text-secondary)' }}>Trade Size Distribution</h4>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distributionData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
            <XAxis
              dataKey="name"
              stroke="var(--text-tertiary)"
              style={{ fontSize: 11 }}
              tick={{ fill: 'var(--text-tertiary)' }}
            />
            <YAxis
              stroke="var(--text-tertiary)"
              style={{ fontSize: 11 }}
              tick={{ fill: 'var(--text-tertiary)' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {distributionData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
          Small: 0-1%, Medium: 1-5%, Large: 5%+
        </div>
      </Card>

      {/* MAE/MFE Analysis */}
      {(analysis.avg_mae !== null || analysis.avg_mfe !== null) && (
        <Card>
          <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>MAE/MFE Analysis</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            {analysis.avg_mae !== null && (
              <MetricItem
                label="Average MAE"
                value={`${formatNumber(analysis.avg_mae)}%`}
                tooltip="Maximum Adverse Excursion - Maximum loss after entry"
                valueColor="var(--color-danger)"
              />
            )}
            {analysis.avg_mfe !== null && (
              <MetricItem
                label="Average MFE"
                value={`${formatNumber(analysis.avg_mfe)}%`}
                tooltip="Maximum Favorable Excursion - Maximum profit after entry"
                valueColor="var(--color-success)"
              />
            )}
            {analysis.avg_efficiency !== null && (
              <MetricItem
                label="Average Efficiency"
                value={`${formatNumber(analysis.avg_efficiency)}%`}
                tooltip="Realization efficiency - Ratio of realized profit to maximum profit"
              />
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

interface MetricItemProps {
  label: string;
  value: string | number;
  tooltip?: string;
  valueColor?: string;
}

function MetricItem({ label, value, tooltip, valueColor }: MetricItemProps) {
  return (
    <div
      style={{
        padding: '12px 15px',
        background: 'var(--bg-tertiary)',
        borderRadius: '6px',
        border: '1px solid var(--border-primary)',
      }}
    >
      <div
        style={{
          fontSize: '10px',
          color: 'var(--text-tertiary)',
          marginBottom: '6px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
        title={tooltip}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: '20px',
          fontWeight: 700,
          color: valueColor || 'var(--text-primary)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
