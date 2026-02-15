// Drawdown chart using Recharts
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { EquityPoint } from '../../types/backtest';
import { useMemo } from 'react';

interface DrawdownChartProps {
  equityCurve: EquityPoint[];
}

export default function DrawdownChart({ equityCurve }: DrawdownChartProps) {
  const drawdownData = useMemo(() => {
    let peak = 0;
    return equityCurve.map((point) => {
      const equity = point.equity;
      if (equity > peak) {
        peak = equity;
      }
      const drawdown = peak > 0 ? ((equity - peak) / peak) * 100 : 0;
      return {
        timestamp: new Date(point.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        drawdown: drawdown,
      };
    });
  }, [equityCurve]);

  const maxDrawdown = Math.min(...drawdownData.map((d) => d.drawdown));

  return (
    <>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={drawdownData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-danger)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--color-danger)" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis
            dataKey="timestamp"
            stroke="var(--text-tertiary)"
            style={{ fontSize: 12 }}
            tick={{ fill: 'var(--text-tertiary)' }}
          />
          <YAxis
            stroke="var(--text-tertiary)"
            style={{ fontSize: 12 }}
            tick={{ fill: 'var(--text-tertiary)' }}
            tickFormatter={(value) => `${value.toFixed(1)}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
            }}
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Drawdown']}
            labelStyle={{ color: 'var(--color-binance)' }}
          />
          <ReferenceLine y={0} stroke="var(--chart-neutral)" strokeDasharray="3 3" />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="var(--color-danger)"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorDrawdown)"
          />
        </AreaChart>
      </ResponsiveContainer>
      <div style={{ textAlign: 'center', marginTop: '10px', color: 'var(--color-danger)', fontSize: '14px', fontWeight: 500 }}>
        Max Drawdown: <strong>{maxDrawdown.toFixed(2)}%</strong>
      </div>
    </>
  );
}
