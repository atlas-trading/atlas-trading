// Backtest Run Page - Execute new backtests
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';

export default function BacktestRun() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [strategyName, setStrategyName] = useState('Golden Cross');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commissionRate, setCommissionRate] = useState(0.001);

  const runBacktest = async () => {
    try {
      setLoading(true);
      setError(null);

      // TODO: Implement backtest API call
      // const response = await backtestAPI.runBacktest({...});

      setError('⚠️ Backtest execution not implemented yet. This feature requires:\n1. Historical data source\n2. Background worker queue\n3. Database integration');

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ margin: 0, marginBottom: '10px' }}>Run New Backtest</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
          Execute a new backtest with your selected parameters
        </p>
      </div>

      <Card>
        <h2 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Configuration</h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Strategy Selection */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Strategy
            </label>
            <select
              value={strategyName}
              onChange={(e) => setStrategyName(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            >
              <option value="Golden Cross">Golden Cross (SMA 50/200)</option>
              <option value="Mean Reversion" disabled>Mean Reversion (Coming Soon)</option>
              <option value="Momentum" disabled>Momentum (Coming Soon)</option>
            </select>
          </div>

          {/* Symbol */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Symbol
            </label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            />
          </div>

          {/* Initial Capital */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Initial Capital ($)
            </label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            />
          </div>

          {/* Commission Rate */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Commission Rate (%)
            </label>
            <input
              type="number"
              step="0.001"
              value={commissionRate * 100}
              onChange={(e) => setCommissionRate(Number(e.target.value) / 100)}
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            />
          </div>

          {/* Warning Box */}
          <div style={{
            padding: '15px',
            background: 'rgba(240, 185, 11, 0.1)',
            border: '1px solid #F0B90B',
            borderRadius: '6px',
            color: 'var(--text-secondary)',
            fontSize: '13px',
          }}>
            <strong style={{ color: '#F0B90B' }}>⚠️ TODO: Worker Implementation Required</strong>
            <ul style={{ margin: '10px 0 0 20px', padding: 0 }}>
              <li>Backtest execution should run in background worker (Celery/RQ)</li>
              <li>Historical data fetching from external API needed</li>
              <li>Currently runs synchronously - may timeout for long periods</li>
            </ul>
          </div>

          {error && (
            <div style={{
              padding: '15px',
              background: 'rgba(246, 70, 93, 0.1)',
              border: '1px solid var(--color-danger)',
              borderRadius: '6px',
              color: 'var(--color-danger)',
              fontSize: '13px',
              whiteSpace: 'pre-wrap',
            }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <button
              onClick={runBacktest}
              disabled={loading}
              className="btn-primary"
              style={{ flex: 1, padding: '12px' }}
            >
              {loading ? 'Running Backtest...' : 'Run Backtest'}
            </button>
            <button
              onClick={() => navigate('/backtests')}
              className="btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              Cancel
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
