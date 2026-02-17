// Position table component for paper trading
interface Position {
  symbol: string;
  side: 'long' | 'short';
  entry_price: number;
  current_price: number;
  quantity: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface PositionTableProps {
  positions: Position[];
}

export default function PositionTable({ positions }: PositionTableProps) {
  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPnLColor = (value: number) => {
    if (value > 0) return 'var(--color-success)';
    if (value < 0) return 'var(--color-danger)';
    return 'var(--text-secondary)';
  };

  if (positions.length === 0) {
    return (
      <div
        style={{
          padding: '40px 20px',
          textAlign: 'center',
          color: 'var(--text-secondary)',
          background: 'var(--bg-tertiary)',
          borderRadius: '8px',
          border: '1px solid var(--border-primary)',
        }}
      >
        No open positions
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'var(--bg-tertiary)',
        borderRadius: '8px',
        border: '1px solid var(--border-primary)',
        overflow: 'hidden',
      }}
    >
      <div style={{ overflowX: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
          }}
        >
          <thead>
            <tr
              style={{
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-primary)',
              }}
            >
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'left',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Symbol
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'left',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Side
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'right',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Entry Price
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'right',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Current Price
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'right',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Quantity
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'right',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Unrealized PnL
              </th>
              <th
                style={{
                  padding: '12px 16px',
                  textAlign: 'right',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Unrealized PnL %
              </th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position, index) => (
              <tr
                key={`${position.symbol}-${index}`}
                style={{
                  borderBottom: index < positions.length - 1 ? '1px solid var(--border-primary)' : 'none',
                }}
              >
                <td
                  style={{
                    padding: '12px 16px',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {position.symbol}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    fontSize: '14px',
                    fontWeight: 500,
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      backgroundColor: position.side === 'long' ? 'rgba(14, 203, 129, 0.1)' : 'rgba(246, 70, 93, 0.1)',
                      color: position.side === 'long' ? 'var(--color-success)' : 'var(--color-danger)',
                    }}
                  >
                    {position.side}
                  </span>
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    textAlign: 'right',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                  }}
                >
                  {formatCurrency(position.entry_price)}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    textAlign: 'right',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                  }}
                >
                  {formatCurrency(position.current_price)}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    textAlign: 'right',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                  }}
                >
                  {position.quantity.toFixed(4)}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    textAlign: 'right',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: getPnLColor(position.unrealized_pnl),
                  }}
                >
                  {formatCurrency(position.unrealized_pnl)}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    textAlign: 'right',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: getPnLColor(position.unrealized_pnl_pct),
                  }}
                >
                  {formatPercent(position.unrealized_pnl_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
