// Stat card component for paper trading metrics
interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

export default function StatCard({ title, value, change, trend, color }: StatCardProps) {
  const getTrendColor = () => {
    if (trend === 'up') return 'var(--color-success)';
    if (trend === 'down') return 'var(--color-danger)';
    return 'var(--text-secondary)';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '▲';
    if (trend === 'down') return '▼';
    return '●';
  };

  const valueColor = color || 'var(--text-primary)';

  return (
    <div
      className="bg-gray-800 rounded-lg border border-gray-700 p-5 shadow-md hover:shadow-lg transition-shadow"
    >
      <div className="flex justify-between items-start mb-2">
        <div
          className="text-xs text-gray-400 uppercase tracking-wider font-medium"
        >
          {title}
        </div>
      </div>

      <div
        className="text-3xl font-bold mb-2"
        style={{ color: valueColor }}
      >
        {value}
      </div>

      {change !== undefined && (
        <div
          className="text-sm font-medium"
          style={{ color: getTrendColor() }}
        >
          {getTrendIcon()} {Math.abs(change).toFixed(2)}%
        </div>
      )}
    </div>
  );
}
