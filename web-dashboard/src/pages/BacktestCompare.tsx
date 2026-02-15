// Backtest comparison page
import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { backtestAPI } from '../services/api';
import type { BacktestRunSummary, BacktestRunFull } from '../types/backtest';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';

const COLORS = ['#F0B90B', '#0ECB81', '#F6465D', '#00C9FF', '#9C27B0', '#FF6B00'];

export default function BacktestCompare() {
  const [allBacktests, setAllBacktests] = useState<BacktestRunSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [compareData, setCompareData] = useState<BacktestRunFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 필터링
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStrategy, setFilterStrategy] = useState<string>('');
  const [filterSymbol, setFilterSymbol] = useState<string>('');

  useEffect(() => {
    loadBacktests();
  }, []);

  const loadBacktests = async () => {
    try {
      setLoading(true);
      const data = await backtestAPI.listBacktests({ limit: 100 });
      setAllBacktests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load backtest list.');
    } finally {
      setLoading(false);
    }
  };

  const loadCompareData = async () => {
    if (selectedIds.size === 0) {
      setCompareData([]);
      return;
    }

    try {
      setLoadingCompare(true);
      const promises = Array.from(selectedIds).map(id => backtestAPI.getBacktestFull(id));
      const results = await Promise.all(promises);
      setCompareData(results);
    } catch (err) {
      console.error('Failed to load comparison data:', err);
    } finally {
      setLoadingCompare(false);
    }
  };

  useEffect(() => {
    loadCompareData();
  }, [selectedIds]);

  const toggleSelection = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      if (newSet.size >= 5) {
        alert('You can compare up to 5 backtests.');
        return;
      }
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  // 필터링된 백테스트
  const filteredBacktests = allBacktests.filter(bt => {
    if (searchTerm && !bt.strategy_name.toLowerCase().includes(searchTerm.toLowerCase()) && !bt.symbol.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (filterStrategy && bt.strategy_name !== filterStrategy) return false;
    if (filterSymbol && bt.symbol !== filterSymbol) return false;
    return true;
  });

  // 고유 전략 및 심볼 목록
  const uniqueStrategies = Array.from(new Set(allBacktests.map(bt => bt.strategy_name)));
  const uniqueSymbols = Array.from(new Set(allBacktests.map(bt => bt.symbol)));

  // Equity Curve 차트 데이터 준비
  const prepareChartData = () => {
    if (compareData.length === 0) return [];

    // 모든 타임스탬프 수집
    const allTimestamps = new Set<string>();
    compareData.forEach(bt => {
      bt.equity_curve.forEach(point => {
        allTimestamps.add(point.timestamp);
      });
    });

    const sortedTimestamps = Array.from(allTimestamps).sort();

    // 각 타임스탬프에 대해 모든 백테스트의 equity 매핑
    return sortedTimestamps.map(timestamp => {
      const point: any = { timestamp: new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) };

      compareData.forEach((bt, idx) => {
        const equityPoint = bt.equity_curve.find(e => e.timestamp === timestamp);
        if (equityPoint) {
          point[`bt_${bt.id}`] = equityPoint.equity;
        }
      });

      return point;
    });
  };

  const chartData = prepareChartData();

  if (loading) {
    return <LoadingSpinner fullScreen />;
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--color-danger)' }}>⚠️ Error</h2>
        <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1600px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '10px' }}>Backtest Comparison</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '30px', fontSize: '14px' }}>
        Select up to 5 backtests to compare.
      </p>

      {/* Filters */}
      <Card style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search strategy or symbol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              flex: '1',
              minWidth: '200px',
              padding: '10px 15px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          />
          <select
            value={filterStrategy}
            onChange={(e) => setFilterStrategy(e.target.value)}
            style={{
              padding: '10px 15px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          >
            <option value="">All Strategies</option>
            {uniqueStrategies.map(strategy => (
              <option key={strategy} value={strategy}>{strategy}</option>
            ))}
          </select>
          <select
            value={filterSymbol}
            onChange={(e) => setFilterSymbol(e.target.value)}
            style={{
              padding: '10px 15px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          >
            <option value="">All Symbols</option>
            {uniqueSymbols.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
          {(searchTerm || filterStrategy || filterSymbol) && (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterStrategy('');
                setFilterSymbol('');
              }}
              className="btn-secondary"
              style={{ padding: '10px 15px' }}
            >
              Reset
            </button>
          )}
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Left: Backtest List */}
        <Card>
          <h2 style={{ marginBottom: '15px' }}>Backtest List ({filteredBacktests.length})</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '15px' }}>
            Selected: {selectedIds.size}/5
          </p>
          <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
            {filteredBacktests.map((bt) => (
              <div
                key={bt.id}
                onClick={() => toggleSelection(bt.id)}
                style={{
                  padding: '12px',
                  marginBottom: '8px',
                  background: selectedIds.has(bt.id) ? 'rgba(240, 185, 11, 0.1)' : 'var(--bg-tertiary)',
                  border: selectedIds.has(bt.id) ? '2px solid var(--color-binance)' : '1px solid var(--border-primary)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                  <span style={{ fontWeight: 600, fontSize: '13px' }}>{bt.strategy_name}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{bt.symbol}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span style={{ color: bt.total_return && bt.total_return >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    {bt.total_return !== null ? `${bt.total_return >= 0 ? '+' : ''}${bt.total_return.toFixed(2)}%` : '-'}
                  </span>
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    MDD: {bt.max_drawdown !== null ? `${bt.max_drawdown.toFixed(2)}%` : '-'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Right: Comparison */}
        <div>
          {selectedIds.size === 0 ? (
            <Card>
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-tertiary)' }}>
                <h3 style={{ marginBottom: '10px' }}>Select Backtests</h3>
                <p style={{ fontSize: '14px' }}>Click backtests from the left list to compare (max 5)</p>
              </div>
            </Card>
          ) : (
            <>
              {loadingCompare ? (
                <LoadingSpinner />
              ) : (
                <>
                  {/* Equity Curve Comparison */}
                  <Card style={{ marginBottom: '20px' }}>
                    <h2 style={{ marginBottom: '20px' }}>Equity Curve Comparison</h2>
                    <ResponsiveContainer width="100%" height={400}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                        <XAxis
                          dataKey="timestamp"
                          stroke="var(--text-tertiary)"
                          style={{ fontSize: 11 }}
                          tick={{ fill: 'var(--text-tertiary)' }}
                        />
                        <YAxis
                          stroke="var(--text-tertiary)"
                          style={{ fontSize: 11 }}
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
                        />
                        <Legend wrapperStyle={{ color: 'var(--text-primary)' }} />
                        {compareData.map((bt, idx) => (
                          <Line
                            key={bt.id}
                            type="monotone"
                            dataKey={`bt_${bt.id}`}
                            name={`${bt.strategy_name} (${bt.symbol})`}
                            stroke={COLORS[idx % COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>

                  {/* Comparison Table */}
                  <Card>
                    <h2 style={{ marginBottom: '20px' }}>Performance Comparison</h2>
                    <div style={{ overflowX: 'auto' }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Strategy</th>
                            <th>Symbol</th>
                            <th>Total Return</th>
                            <th>Final Capital</th>
                            <th>Max Drawdown</th>
                            <th>Sharpe Ratio</th>
                            <th>Total Trades</th>
                            <th>Win Rate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compareData.map((bt, idx) => (
                            <tr key={bt.id}>
                              <td>
                                <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '2px', background: COLORS[idx % COLORS.length], marginRight: '8px' }}></span>
                                {bt.strategy_name}
                              </td>
                              <td>{bt.symbol}</td>
                              <td style={{ color: (bt.total_return ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                                {bt.total_return !== null ? `${bt.total_return >= 0 ? '+' : ''}${bt.total_return.toFixed(2)}%` : '-'}
                              </td>
                              <td>${bt.final_capital?.toLocaleString(undefined, { minimumFractionDigits: 2 }) ?? '-'}</td>
                              <td style={{ color: 'var(--color-danger)' }}>
                                {bt.max_drawdown !== null ? `${bt.max_drawdown.toFixed(2)}%` : '-'}
                              </td>
                              <td>{bt.sharpe_ratio?.toFixed(2) ?? '-'}</td>
                              <td>{bt.total_trades ?? 0}</td>
                              <td>{bt.win_rate !== null ? `${bt.win_rate.toFixed(1)}%` : '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
