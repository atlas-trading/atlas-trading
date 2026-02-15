// Stat card component for displaying KPIs
interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  icon?: string;
}

export default function StatCard({ label, value, change, icon }: StatCardProps) {
  const getChangeColor = () => {
    if (change === undefined || change === 0) return 'var(--text-secondary)';
    return change > 0 ? 'var(--color-success)' : 'var(--color-danger)';
  };

  const getValueColor = () => {
    if (typeof value === 'string' && value.includes('%')) {
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        return numValue >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
      }
    }
    return 'var(--text-primary)';
  };

  return (
    <div
      style={{
        padding: '20px',
        background: 'var(--bg-tertiary)',
        borderRadius: '8px',
        border: '1px solid var(--border-primary)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '8px',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            fontWeight: 500,
          }}
        >
          {label}
        </div>
        {icon && <span style={{ fontSize: '20px' }}>{icon}</span>}
      </div>

      <div
        style={{
          fontSize: '28px',
          fontWeight: 700,
          color: getValueColor(),
          marginBottom: change !== undefined ? '8px' : '0',
        }}
      >
        {value}
      </div>

      {change !== undefined && (
        <div
          style={{
            fontSize: '12px',
            color: getChangeColor(),
            fontWeight: 500,
          }}
        >
          {change > 0 ? '▲' : change < 0 ? '▼' : '●'} {Math.abs(change).toFixed(2)}%
        </div>
      )}
    </div>
  );
}
