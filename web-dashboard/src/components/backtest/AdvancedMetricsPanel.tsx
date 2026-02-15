// Advanced metrics panel
import { useEffect, useState } from 'react';
import { backtestAPI } from '../../services/api';
import type { AdvancedMetrics } from '../../types/backtest';
import Card from '../common/Card';
import LoadingSpinner from '../common/LoadingSpinner';

interface AdvancedMetricsPanelProps {
  backtestId: number;
}

export default function AdvancedMetricsPanel({ backtestId }: AdvancedMetricsPanelProps) {
  const [metrics, setMetrics] = useState<AdvancedMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMetrics();
  }, [backtestId]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await backtestAPI.getAdvancedMetrics(backtestId);
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load advanced metrics.');
      console.error('Failed to load advanced metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error || !metrics) {
    return (
      <Card>
        <p style={{ color: 'var(--color-danger)', textAlign: 'center' }}>
          {error || 'Unable to load data.'}
        </p>
      </Card>
    );
  }

  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div>
      {/* Risk-Adjusted Returns */}
      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Risk-Adjusted Returns</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <MetricItem label="Sortino Ratio" value={formatNumber(metrics.sortino_ratio)} tooltip="Risk-adjusted return considering only downside volatility" />
          <MetricItem label="Calmar Ratio" value={formatNumber(metrics.calmar_ratio)} tooltip="Annualized return / Max drawdown" />
          <MetricItem label="Recovery Factor" value={formatNumber(metrics.recovery_factor)} tooltip="Total return / Max drawdown" />
        </div>
      </Card>

      {/* Profitability Metrics */}
      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Profitability Metrics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <MetricItem
            label="Profit Factor"
            value={formatNumber(metrics.profit_factor)}
            tooltip="Total profit / Total loss (>1 is profitable)"
            valueColor={metrics.profit_factor > 1 ? 'var(--color-success)' : 'var(--color-danger)'}
          />
          <MetricItem
            label="Expectancy"
            value={formatCurrency(metrics.expectancy)}
            tooltip="Average profit per trade"
            valueColor={metrics.expectancy > 0 ? 'var(--color-success)' : 'var(--color-danger)'}
          />
          <MetricItem label="Win/Loss Ratio" value={formatNumber(metrics.win_loss_ratio)} tooltip="Average win size / Average loss size" />
          <MetricItem
            label="Net Profit"
            value={formatCurrency(metrics.net_profit)}
            tooltip="Total net profit"
            valueColor={metrics.net_profit > 0 ? 'var(--color-success)' : 'var(--color-danger)'}
          />
          <MetricItem
            label="Net Profit %"
            value={`${formatNumber(metrics.net_profit_pct)}%`}
            tooltip="Net profit percentage"
            valueColor={metrics.net_profit_pct > 0 ? 'var(--color-success)' : 'var(--color-danger)'}
          />
        </div>
      </Card>

      {/* Trade Statistics */}
      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Trade Statistics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <MetricItem label="Max Consecutive Wins" value={metrics.max_consecutive_wins} tooltip="Maximum number of consecutive winning trades" />
          <MetricItem label="Max Consecutive Losses" value={metrics.max_consecutive_losses} tooltip="Maximum number of consecutive losing trades" />
          <MetricItem
            label="Avg Holding Time"
            value={`${formatNumber(metrics.avg_trade_duration_hours, 1)}h`}
            tooltip="Average position holding time (hours)"
          />
          <MetricItem label="Total Commission" value={formatCurrency(metrics.total_commission_paid)} tooltip="Total trading commission paid" />
        </div>
      </Card>
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
        padding: '15px',
        background: 'var(--bg-tertiary)',
        borderRadius: '6px',
        border: '1px solid var(--border-primary)',
      }}
    >
      <div
        style={{
          fontSize: '11px',
          color: 'var(--text-tertiary)',
          marginBottom: '8px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
        title={tooltip}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: '24px',
          fontWeight: 700,
          color: valueColor || 'var(--text-primary)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
