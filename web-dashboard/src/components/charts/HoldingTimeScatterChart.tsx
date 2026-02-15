// Holding Time vs PnL Scatter Plot
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ZAxis } from 'recharts';
import type { Trade } from '../../types/backtest';

interface HoldingTimeScatterChartProps {
  trades: Trade[];
}

export default function HoldingTimeScatterChart({ trades }: HoldingTimeScatterChartProps) {
  // Calculate holding time and prepare data
  const scatterData = trades
    .filter(t => t.exit_time && t.pnl !== null)
    .map(t => {
      const entryTime = new Date(t.entry_time).getTime();
      const exitTime = new Date(t.exit_time!).getTime();
      const holdingHours = (exitTime - entryTime) / (1000 * 60 * 60);

      return {
        x: holdingHours,
        y: t.pnl!,
        z: Math.abs(t.pnl!), // For sizing (optional)
        color: t.pnl! >= 0 ? '#0ECB81' : '#F6465D',
        isWin: t.pnl! >= 0,
      };
    });

  const winTrades = scatterData.filter(d => d.isWin);
  const lossTrades = scatterData.filter(d => !d.isWin);

  if (scatterData.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
        No trade data available
      </div>
    );
  }

  // Calculate optimal holding time (median of winning trades)
  const winningHoldingTimes = winTrades.map(d => d.x).sort((a, b) => a - b);
  const medianWinHoldingTime = winningHoldingTimes.length > 0
    ? winningHoldingTimes[Math.floor(winningHoldingTimes.length / 2)]
    : 0;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis
          type="number"
          dataKey="x"
          name="Holding Time"
          unit=" hrs"
          stroke="var(--text-tertiary)"
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text-tertiary)' }}
          label={{ value: 'Holding Time (hours)', position: 'insideBottom', offset: -10, fill: 'var(--text-tertiary)' }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="PnL"
          unit=" $"
          stroke="var(--text-tertiary)"
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text-tertiary)' }}
          label={{ value: 'PnL ($)', angle: -90, position: 'insideLeft', fill: 'var(--text-tertiary)' }}
        />
        <ZAxis type="number" dataKey="z" range={[20, 200]} />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          contentStyle={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
          }}
          formatter={(value: number, name: string) => {
            if (name === 'Holding Time') return [`${value.toFixed(1)} hrs`, name];
            if (name === 'PnL') return [`$${value.toFixed(2)}`, name];
            return [value, name];
          }}
        />
        <ReferenceLine y={0} stroke="var(--text-tertiary)" strokeDasharray="3 3" />
        {medianWinHoldingTime > 0 && (
          <ReferenceLine
            x={medianWinHoldingTime}
            stroke="var(--color-success)"
            strokeDasharray="3 3"
            label={{
              value: `Median Win: ${medianWinHoldingTime.toFixed(1)}h`,
              position: 'top',
              fill: 'var(--color-success)',
              fontSize: 11
            }}
          />
        )}
        <Scatter
          name="Winning Trades"
          data={winTrades}
          fill="var(--color-success)"
          opacity={0.6}
        />
        <Scatter
          name="Losing Trades"
          data={lossTrades}
          fill="var(--color-danger)"
          opacity={0.6}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
