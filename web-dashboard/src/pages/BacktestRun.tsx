// Backtest Run Page - Execute new backtests
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import { strategyAPI, marketAPI, type Strategy, type MarketSymbol, type Timeframe } from '../services/api';

export default function BacktestRun() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // API data states
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [symbols, setSymbols] = useState<MarketSymbol[]>([]);
  const [timeframes, setTimeframes] = useState<Timeframe[]>([]);

  // Form states
  const [strategyName, setStrategyName] = useState('');
  const [symbol, setSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commissionRate, setCommissionRate] = useState(0.001);

  // Load data from APIs on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setDataLoading(true);
        setError(null);

        const [strategiesData, symbolsData, timeframesData] = await Promise.all([
          strategyAPI.getAvailableStrategies(),
          marketAPI.getSymbols(),
          marketAPI.getTimeframes(),
        ]);

        setStrategies(strategiesData);
        setSymbols(symbolsData);
        setTimeframes(timeframesData);

        // Set default values to first item from each API
        if (strategiesData.length > 0) {
          setStrategyName(strategiesData[0].name);
        }
        if (symbolsData.length > 0) {
          setSymbol(symbolsData[0].symbol);
        }
        if (timeframesData.length > 0) {
          setTimeframe(timeframesData[0].value);
        }

        // Set default date range (last 90 days)
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 90);
        setEndDate(end.toISOString().split('T')[0]);
        setStartDate(start.toISOString().split('T')[0]);

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load configuration data');
      } finally {
        setDataLoading(false);
      }
    };

    loadData();
  }, []);

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

  if (dataLoading) {
    return (
      <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <h1 style={{ margin: 0, marginBottom: '10px' }}>Run New Backtest</h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Loading configuration...
          </p>
        </div>
      </div>
    );
  }

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
              disabled={strategies.length === 0}
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
              {strategies.length === 0 ? (
                <option value="">No strategies available</option>
              ) : (
                strategies.map((strategy) => (
                  <option key={strategy.name} value={strategy.name}>
                    {strategy.name}
                    {strategy.description ? ` - ${strategy.description}` : ''}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Symbol Selection */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Symbol
            </label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={symbols.length === 0}
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
              {symbols.length === 0 ? (
                <option value="">No symbols available</option>
              ) : (
                symbols.map((sym) => (
                  <option key={sym.symbol} value={sym.symbol}>
                    {sym.symbol}
                    {sym.description ? ` - ${sym.description}` : ''}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Timeframe Selection */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Timeframe
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              disabled={timeframes.length === 0}
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
              {timeframes.length === 0 ? (
                <option value="">No timeframes available</option>
              ) : (
                timeframes.map((tf) => (
                  <option key={tf.value} value={tf.value}>
                    {tf.label}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Date Range */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
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
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
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
