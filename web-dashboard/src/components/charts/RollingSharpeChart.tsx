// Rolling Sharpe Ratio Chart - Detects Regime Collapse
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { EquityPoint } from '../../types/backtest';

interface RollingSharpeChartProps {
  equityCurve: EquityPoint[];
  windowDays?: number;
}

export default function RollingSharpeChart({ equityCurve, windowDays = 90 }: RollingSharpeChartProps) {
  // Calculate daily returns
  const returns: number[] = [];
  for (let i = 1; i < equityCurve.length; i++) {
    const prevEquity = equityCurve[i - 1].equity;
    const currEquity = equityCurve[i].equity;
    const dailyReturn = ((currEquity - prevEquity) / prevEquity) * 100;
    returns.push(dailyReturn);
  }

  // Calculate rolling Sharpe
  const rollingSharpe: { date: string; sharpe: number }[] = [];

  for (let i = windowDays; i < returns.length; i++) {
    const windowReturns = returns.slice(i - windowDays, i);

    // Calculate mean and std
    const mean = windowReturns.reduce((a, b) => a + b, 0) / windowReturns.length;
    const variance = windowReturns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / windowReturns.length;
    const std = Math.sqrt(variance);

    // Sharpe ratio (annualized, assuming 252 trading days)
    const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;

    rollingSharpe.push({
      date: new Date(equityCurve[i].timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      sharpe: sharpe,
    });
  }

  if (rollingSharpe.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
        Not enough data for {windowDays}-day rolling Sharpe calculation
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={rollingSharpe}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis
          dataKey="date"
          stroke="var(--text-tertiary)"
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text-tertiary)' }}
        />
        <YAxis
          stroke="var(--text-tertiary)"
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text-tertiary)' }}
          label={{ value: 'Sharpe Ratio', angle: -90, position: 'insideLeft', fill: 'var(--text-tertiary)' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
          }}
          formatter={(value: number) => [value.toFixed(2), 'Sharpe']}
        />
        <ReferenceLine y={0} stroke="var(--text-tertiary)" strokeDasharray="3 3" />
        <ReferenceLine y={1} stroke="var(--color-success)" strokeDasharray="3 3" label={{ value: 'Good (>1)', position: 'right', fill: 'var(--color-success)', fontSize: 10 }} />
        <Line
          type="monotone"
          dataKey="sharpe"
          stroke="var(--color-binance)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
