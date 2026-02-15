import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';

interface StrategyConfig {
  id: number;
  strategy_name: string;
  display_name: string;
  description: string;
  parameters: Record<string, any>;
  is_active: boolean;
  is_live: boolean;
  created_at: string;
  updated_at: string;
  last_backtest_return: number | null;
  last_backtest_sharpe: number | null;
}

interface AvailableStrategy {
  strategy_name: string;
  display_name: string;
  description: string;
  parameter_schema: Array<{
    name: string;
    type: string;
    default: any;
    description: string;
  }>;
}

export default function StrategyList() {
  const [configs, setConfigs] = useState<StrategyConfig[]>([]);
  const [availableStrategies, setAvailableStrategies] = useState<AvailableStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [configsRes, availableRes] = await Promise.all([
        api.get('/strategies/configs'),
        api.get('/strategies/available')
      ]);
      setConfigs(configsRes.data);
      setAvailableStrategies(availableRes.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load strategies');
      console.error('Error loading strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleActive = async (strategyName: string, currentState: boolean) => {
    try {
      await api.put(`/strategies/configs/${strategyName}`, {
        is_active: !currentState
      });
      fetchData();
    } catch (err: any) {
      alert(`Failed to update strategy: ${err.message}`);
    }
  };

  const deleteStrategy = async (strategyName: string) => {
    if (!confirm(`Are you sure you want to delete ${strategyName}?`)) {
      return;
    }

    try {
      await api.delete(`/strategies/configs/${strategyName}`);
      fetchData();
    } catch (err: any) {
      alert(`Failed to delete strategy: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Loading strategies...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Strategy Management</h1>
        <p className="page-description">
          Manage trading strategies and their parameters
        </p>
      </div>

      {/* Configured Strategies */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Configured Strategies ({configs.length})</h2>
        </div>
        <div className="card-body">
          {configs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
              No strategies configured yet. Add a strategy below.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Description</th>
                  <th>Parameters</th>
                  <th>Status</th>
                  <th>Last Backtest</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((config) => (
                  <tr key={config.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{config.display_name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        {config.strategy_name}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '300px' }}>
                        {config.description || '-'}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontSize: '12px', fontFamily: 'monospace' }}>
                        {Object.keys(config.parameters).length} params
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span
                          className={config.is_active ? 'text-success' : 'text-muted'}
                          style={{ fontSize: '12px', fontWeight: 500 }}
                        >
                          {config.is_active ? 'Active' : 'Inactive'}
                        </span>
                        {config.is_live && (
                          <span style={{
                            fontSize: '10px',
                            padding: '2px 6px',
                            background: 'var(--color-danger)',
                            color: 'white',
                            borderRadius: '4px',
                            fontWeight: 600
                          }}>
                            LIVE
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      {config.last_backtest_return !== null ? (
                        <div>
                          <div className={config.last_backtest_return >= 0 ? 'text-success' : 'text-danger'}>
                            {config.last_backtest_return >= 0 ? '+' : ''}{config.last_backtest_return}%
                          </div>
                          {config.last_backtest_sharpe !== null && (
                            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                              Sharpe: {config.last_backtest_sharpe.toFixed(2)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-tertiary)' }}>-</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <Link to={`/strategies/edit/${config.strategy_name}`}>
                          <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '13px' }}>
                            Edit
                          </button>
                        </Link>
                        <button
                          onClick={() => toggleActive(config.strategy_name, config.is_active)}
                          className="btn-secondary"
                          style={{ padding: '6px 12px', fontSize: '13px' }}
                        >
                          {config.is_active ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          onClick={() => deleteStrategy(config.strategy_name)}
                          className="btn-secondary"
                          style={{
                            padding: '6px 12px',
                            fontSize: '13px',
                            color: 'var(--color-danger)',
                            borderColor: 'var(--color-danger)'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Available Strategies to Add */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header">
          <h2 className="card-title">Available Strategies ({availableStrategies.length})</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {availableStrategies.map((strategy) => {
              const isConfigured = configs.some(c => c.strategy_name === strategy.strategy_name);

              return (
                <div
                  key={strategy.strategy_name}
                  className="action-card"
                  style={{
                    opacity: isConfigured ? 0.6 : 1,
                    cursor: isConfigured ? 'not-allowed' : 'pointer'
                  }}
                >
                  <h3>{strategy.display_name}</h3>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                    {strategy.description || 'No description'}
                  </p>
                  <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                    {strategy.parameter_schema.length} parameters
                  </div>
                  {isConfigured ? (
                    <div style={{ marginTop: '16px', fontSize: '13px', color: 'var(--color-success)' }}>
                      ✓ Already configured
                    </div>
                  ) : (
                    <Link to={`/strategies/add/${strategy.strategy_name}`}>
                      <button className="btn-primary" style={{ marginTop: '16px', width: '100%' }}>
                        Add Strategy
                      </button>
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
