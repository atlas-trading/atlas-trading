// Live equity curve chart for paper trading with real-time updates
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface SnapshotPoint {
  timestamp: string;
  balance: number;
  equity: number;
}

interface LiveEquityCurveChartProps {
  snapshots: SnapshotPoint[];
  initialCapital: number;
}

export default function LiveEquityCurveChart({ snapshots, initialCapital }: LiveEquityCurveChartProps) {
  const chartData = snapshots.map((point) => ({
    timestamp: new Date(point.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }),
    balance: point.balance,
    equity: point.equity,
    initial: initialCapital,
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
          tickFormatter={(value) => `$${value.toLocaleString()}`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
          }}
          formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
          labelStyle={{ color: 'var(--color-binance)' }}
        />
        <Legend
          wrapperStyle={{ color: 'var(--text-primary)' }}
          iconType="line"
        />
        <Line
          type="monotone"
          dataKey="equity"
          name="Equity"
          stroke="var(--color-binance)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="balance"
          name="Balance"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="initial"
          name="Initial Capital"
          stroke="var(--chart-neutral)"
          strokeWidth={1}
          strokeDasharray="5 5"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
