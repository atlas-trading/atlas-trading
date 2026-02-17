import type { PaperTradingTrade } from '../../types/paper_trading';

interface TradeDetailPanelProps {
  trade: PaperTradingTrade | null;
  onClose: () => void;
}

export default function TradeDetailPanel({ trade, onClose }: TradeDetailPanelProps) {
  if (!trade) return null;

  const formatCurrency = (value: number | null) => {
    if (value === null) return '-';
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const calculateHoldingTime = () => {
    if (!trade.exit_price) return 'Position Open';

    const entryTime = new Date(trade.timestamp).getTime();
    const exitTime = new Date().getTime(); // Approximate - would need actual exit timestamp
    const diffMs = exitTime - entryTime;

    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const isProfitable = trade.pnl !== null && trade.pnl >= 0;
  const isBuy = trade.side === 'buy';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '420px',
        background: 'var(--bg-secondary)',
        borderLeft: '1px solid var(--border-primary)',
        boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.3)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        animation: 'slideInRight 0.3s ease-out',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '24px',
          borderBottom: '1px solid var(--border-primary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'var(--bg-tertiary)',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: 'var(--color-binance)', marginBottom: '4px' }}>
            Trade Details
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            ID: #{trade.id}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-hover)';
            e.currentTarget.style.borderColor = 'var(--color-danger)';
            e.currentTarget.style.color = 'var(--color-danger)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--bg-secondary)';
            e.currentTarget.style.borderColor = 'var(--border-primary)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {/* Symbol & Side Badge */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {trade.symbol}
            </span>
            <span
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                background: isBuy ? 'rgba(14, 203, 129, 0.15)' : 'rgba(246, 70, 93, 0.15)',
                color: isBuy ? '#0ECB81' : '#F6465D',
                border: `1px solid ${isBuy ? '#0ECB81' : '#F6465D'}`,
              }}
            >
              {trade.side}
            </span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            Position: {trade.position_side}
            {trade.position_type && ` • Type: ${trade.position_type}`}
          </div>
        </div>

        {/* PnL Card */}
        {trade.pnl !== null && (
          <div
            style={{
              padding: '20px',
              borderRadius: '12px',
              background: isProfitable
                ? 'linear-gradient(135deg, rgba(14, 203, 129, 0.15) 0%, rgba(14, 203, 129, 0.05) 100%)'
                : 'linear-gradient(135deg, rgba(246, 70, 93, 0.15) 0%, rgba(246, 70, 93, 0.05) 100%)',
              border: `1px solid ${isProfitable ? 'rgba(14, 203, 129, 0.3)' : 'rgba(246, 70, 93, 0.3)'}`,
              marginBottom: '24px',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
              Profit & Loss
            </div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: isProfitable ? '#0ECB81' : '#F6465D', marginBottom: '4px' }}>
              {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
            </div>
            {trade.pnl_percent !== null && (
              <div style={{ fontSize: '16px', fontWeight: 600, color: isProfitable ? '#0ECB81' : '#F6465D', opacity: 0.8 }}>
                {formatPercent(trade.pnl_percent)}
              </div>
            )}
          </div>
        )}

        {/* Price Information */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Price Information
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div
              style={{
                padding: '16px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '8px',
              }}
            >
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Entry Price
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#0ECB81' }}>
                {formatCurrency(trade.entry_price)}
              </div>
            </div>
            <div
              style={{
                padding: '16px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '8px',
              }}
            >
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Exit Price
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: trade.exit_price ? '#F6465D' : 'var(--text-tertiary)' }}>
                {formatCurrency(trade.exit_price)}
              </div>
            </div>
          </div>
        </div>

        {/* Trade Metrics */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Trade Metrics
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <MetricRow label="Quantity" value={trade.quantity.toFixed(4)} />
            <MetricRow label="Commission" value={formatCurrency(trade.commission)} />
            <MetricRow label="Slippage" value={formatCurrency(trade.slippage)} />
            <MetricRow label="Holding Time" value={calculateHoldingTime()} />
          </div>
        </div>

        {/* Risk Management */}
        {(trade.stop_loss !== null || trade.take_profit !== null) && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Risk Management
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {trade.stop_loss !== null && (
                <MetricRow label="Stop Loss" value={formatCurrency(trade.stop_loss)} color="#F6465D" />
              )}
              {trade.take_profit !== null && (
                <MetricRow label="Take Profit" value={formatCurrency(trade.take_profit)} color="#0ECB81" />
              )}
            </div>
          </div>
        )}

        {/* Exit Reason */}
        {trade.exit_reason && (
          <div
            style={{
              padding: '16px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '8px',
              marginBottom: '24px',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Exit Reason
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-primary)', fontWeight: 500 }}>
              {trade.exit_reason}
            </div>
          </div>
        )}

        {/* Timestamp */}
        <div
          style={{
            padding: '16px',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '8px',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Executed At
          </div>
          <div style={{ fontSize: '14px', color: 'var(--text-primary)', fontWeight: 500 }}>
            {formatDateTime(trade.timestamp)}
          </div>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

// Helper Component
interface MetricRowProps {
  label: string;
  value: string;
  color?: string;
}

function MetricRow({ label, value, color }: MetricRowProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 16px',
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-primary)',
        borderRadius: '8px',
      }}
    >
      <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontSize: '14px', fontWeight: 600, color: color || 'var(--text-primary)' }}>{value}</span>
    </div>
  );
}
