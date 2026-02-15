// Backtest list page
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { backtestAPI } from '../services/api';
import type { BacktestRunSummary } from '../types/backtest';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function BacktestList() {
  const [backtests, setBacktests] = useState<BacktestRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadBacktests();
  }, []);

  const loadBacktests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await backtestAPI.listBacktests({ limit: 20 });
      setBacktests(data);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load backtest list';
      setError(errorMsg);
      console.error('Failed to load backtests:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return '-';
    const color = value >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
    return <span style={{ color }}>{value.toFixed(2)}%</span>;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US');
  };

  if (loading) {
    return <LoadingSpinner fullScreen />;
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--color-danger)' }}>⚠️ Error</h2>
        <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <button onClick={loadBacktests} className="btn-primary" style={{ marginTop: '20px' }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Atlas Trading - Backtest Results</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => navigate('/backtests/run')}
            className="btn-primary"
            style={{ padding: '10px 20px' }}
          >
            New Backtest
          </button>
          <button
            onClick={() => navigate('/compare')}
            className="btn-secondary"
            style={{ padding: '10px 20px' }}
          >
            Compare
          </button>
        </div>
      </div>

      <Card>
        <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Backtest List</h2>
          <button onClick={loadBacktests} className="btn-secondary">
            Refresh
          </button>
        </div>

        {backtests.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            No backtest results available.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Strategy</th>
                  <th>Symbol</th>
                  <th>Timeframe</th>
                  <th>Return</th>
                  <th>MDD</th>
                  <th>Sharpe</th>
                  <th>Trades</th>
                  <th>Win Rate</th>
                  <th>Period</th>
                </tr>
              </thead>
              <tbody>
                {backtests.map((bt) => (
                  <tr
                    key={bt.id}
                    onClick={() => navigate(`/backtest/${bt.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{bt.id}</td>
                    <td style={{ fontWeight: 600 }}>{bt.strategy_name}</td>
                    <td>{bt.symbol}</td>
                    <td>{bt.timeframe}</td>
                    <td>{formatPercent(bt.total_return)}</td>
                    <td>
                      <span style={{ color: 'var(--color-danger)' }}>
                        {bt.max_drawdown !== null ? `${bt.max_drawdown.toFixed(2)}%` : '-'}
                      </span>
                    </td>
                    <td>{bt.sharpe_ratio !== null ? bt.sharpe_ratio.toFixed(2) : '-'}</td>
                    <td>{bt.total_trades ?? '-'}</td>
                    <td>{bt.win_rate !== null ? `${bt.win_rate.toFixed(1)}%` : '-'}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                      {formatDate(bt.start_date)} ~ {formatDate(bt.end_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
