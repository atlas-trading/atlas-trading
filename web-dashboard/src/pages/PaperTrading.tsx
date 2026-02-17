import { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Card from '../components/common/Card';
import StatCard from '../components/common/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ChartSection from '../components/paper_trading/ChartSection';
import TradingViewWidget from '../components/charts/TradingViewWidget';
import apiClient from '../services/api';
import { paperTradingAPI } from '../services/paperTradingApi';
import type {
  PaperTradingSession,
  PaperTradingSessionCreate,
  PaperTradingSnapshot,
  PaperTradingTrade,
  KlineData,
} from '../types/paper_trading';

export default function PaperTrading() {
  const [sessions, setSessions] = useState<PaperTradingSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [sessionData, setSessionData] = useState<PaperTradingSession | null>(null);
  const [snapshots, setSnapshots] = useState<PaperTradingSnapshot[]>([]);
  const [klineData, setKlineData] = useState<KlineData[]>([]);
  const [interval, setInterval] = useState<string>('1m');
  const [positions, setPositions] = useState<any[]>([]);
  const [recentTrades, setRecentTrades] = useState<PaperTradingTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewSessionModal, setShowNewSessionModal] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [chartType, setChartType] = useState<'lightweight' | 'tradingview'>('tradingview');

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Auto-select first active session
  useEffect(() => {
    if (sessions.length > 0 && !selectedSessionId) {
      const activeSession = sessions.find(s => s.status === 'active') || sessions[0];
      setSelectedSessionId(activeSession.id);
    }
  }, [sessions, selectedSessionId]);

  // Load session details when selected or interval changes
  useEffect(() => {
    if (selectedSessionId) {
      loadSessionDetails();
      setIsPolling(true);
    } else {
      setIsPolling(false);
    }
  }, [selectedSessionId, interval]);

  // Real-time polling (every 5 seconds)
  useEffect(() => {
    if (!isPolling || !selectedSessionId) return;

    const interval = setInterval(() => {
      loadSessionDetails(true); // silent refresh
    }, 5000);

    return () => clearInterval(interval);
  }, [isPolling, selectedSessionId]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('📡 Loading sessions...');
      const response = await apiClient.get<PaperTradingSession[]>('/paper-trading/sessions');
      console.log('✅ Sessions loaded:', response.data);
      setSessions(response.data);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load sessions';
      setError(errorMsg);
      console.error('❌ Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSessionDetails = async (silent = false) => {
    if (!selectedSessionId) return;

    try {
      if (!silent) setLoading(true);
      setError(null);

      // Parallel fetch
      const [sessionRes, snapshotsRes, tradesRes, klinesRes] = await Promise.all([
        apiClient.get<PaperTradingSession>(`/paper-trading/sessions/${selectedSessionId}`),
        apiClient.get<PaperTradingSnapshot[]>(`/paper-trading/sessions/${selectedSessionId}/snapshots?limit=50`),
        apiClient.get<PaperTradingTrade[]>(`/paper-trading/sessions/${selectedSessionId}/trades?limit=20`),
        paperTradingAPI.getSessionKlines(selectedSessionId, interval, 200).catch(() => []),
      ]);

      setSessionData(sessionRes.data);
      setSnapshots(snapshotsRes.data);
      setRecentTrades(tradesRes.data);
      setKlineData(klinesRes);

      // Extract current positions from latest snapshot
      if (snapshotsRes.data.length > 0) {
        const latestSnapshot = snapshotsRes.data[0];
        setPositions(latestSnapshot.open_positions || []);
      }
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Failed to load session details');
      }
      console.error('Failed to load session details:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const createNewSession = async (data: PaperTradingSessionCreate) => {
    try {
      setLoading(true);
      await apiClient.post('/paper-trading/sessions', data);
      await loadSessions();
      setShowNewSessionModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      console.error('Failed to create session:', err);
    } finally {
      setLoading(false);
    }
  };

  const controlSession = async (action: 'start' | 'pause' | 'stop') => {
    if (!selectedSessionId) return;

    try {
      await paperTradingAPI.controlSession(selectedSessionId, action);
      await loadSessionDetails(); // Refresh session data
      await loadSessions(); // Refresh session list
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} session`);
      console.error(`Failed to ${action} session:`, err);
    }
  };

  const deleteSession = async () => {
    if (!selectedSessionId) return;

    const confirmed = window.confirm(
      'Are you sure you want to delete this session? This action cannot be undone.'
    );

    if (!confirmed) return;

    try {
      setLoading(true);
      await paperTradingAPI.deleteSession(selectedSessionId);
      setSelectedSessionId(null);
      await loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
      console.error('Failed to delete session:', err);
    } finally {
      setLoading(false);
    }
  };

  // Format utilities
  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  };

  // Chart data
  const equityChartData = useMemo(() => {
    return snapshots.map(snap => ({
      timestamp: formatDateTime(snap.timestamp),
      equity: snap.equity,
      balance: snap.balance,
    })).reverse();
  }, [snapshots]);

  // Metrics calculations
  const winRate = sessionData
    ? sessionData.total_trades > 0
      ? (sessionData.winning_trades / sessionData.total_trades) * 100
      : 0
    : 0;

  const totalPnlPct = sessionData
    ? (sessionData.total_pnl / sessionData.initial_capital) * 100
    : 0;

  if (loading && !sessionData) {
    return <LoadingSpinner fullScreen />;
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ marginBottom: '8px' }}>Paper Trading Monitor</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Real-time simulation with live market data
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Session Selector */}
          {sessions.length > 0 && (
            <select
              value={selectedSessionId || ''}
              onChange={(e) => setSelectedSessionId(Number(e.target.value))}
              style={{
                padding: '10px 16px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                cursor: 'pointer',
                minWidth: '200px',
              }}
            >
              {sessions.map(session => (
                <option key={session.id} value={session.id}>
                  {session.name || `Session #${session.id}`} - {session.status.toUpperCase()}
                </option>
              ))}
            </select>
          )}

          {/* New Session Button */}
          <button
            onClick={() => setShowNewSessionModal(true)}
            className="btn-primary"
            style={{ whiteSpace: 'nowrap' }}
          >
            + New Session
          </button>

          {/* Live Indicator */}
          {sessionData?.status === 'active' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              background: 'rgba(14, 203, 129, 0.1)',
              border: '1px solid var(--color-success)',
              borderRadius: '6px',
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--color-success)',
                animation: 'pulse 2s infinite',
              }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-success)' }}>
                LIVE
              </span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div style={{
          padding: '15px',
          background: 'rgba(246, 70, 93, 0.1)',
          border: '1px solid var(--color-danger)',
          borderRadius: '8px',
          marginBottom: '20px',
          color: 'var(--color-danger)',
        }}>
          {error}
        </div>
      )}

      {sessionData ? (
        <>
          {/* Stats Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '15px',
            marginBottom: '30px',
          }}>
            <StatCard
              label="Balance"
              value={formatCurrency(sessionData.current_balance)}
            />
            <StatCard
              label="Equity"
              value={formatCurrency(sessionData.current_equity)}
            />
            <StatCard
              label="Total PnL"
              value={formatCurrency(sessionData.total_pnl)}
            />
            <StatCard
              label="PnL %"
              value={formatPercent(totalPnlPct)}
            />
            <StatCard
              label="Win Rate"
              value={`${winRate.toFixed(1)}%`}
            />
            <StatCard
              label="Total Trades"
              value={sessionData.total_trades}
            />
            <StatCard
              label="Max Drawdown"
              value={formatPercent(sessionData.max_drawdown)}
            />
            <StatCard
              label="Commission Paid"
              value={formatCurrency(sessionData.total_commission)}
            />
          </div>

          {/* Session Info Banner */}
          <div style={{
            padding: '15px 20px',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: '8px',
            marginBottom: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', gap: '30px' }}>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Strategy
                </span>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-binance)', marginTop: '4px' }}>
                  {sessionData.strategy}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Symbol
                </span>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {sessionData.symbol}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Started
                </span>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {formatDateTime(sessionData.start_time)}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{
                padding: '6px 12px',
                background: sessionData.status === 'active' ? 'rgba(14, 203, 129, 0.1)' : 'rgba(132, 142, 156, 0.1)',
                border: `1px solid ${sessionData.status === 'active' ? 'var(--color-success)' : 'var(--text-tertiary)'}`,
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: sessionData.status === 'active' ? 'var(--color-success)' : 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                {sessionData.status}
              </div>

              {/* Control Buttons */}
              {sessionData.status === 'active' ? (
                <>
                  <button
                    onClick={() => controlSession('pause')}
                    style={{
                      padding: '6px 12px',
                      background: 'rgba(255, 193, 7, 0.1)',
                      border: '1px solid #FFC107',
                      borderRadius: '6px',
                      color: '#FFC107',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                    }}
                  >
                    Pause
                  </button>
                  <button
                    onClick={() => controlSession('stop')}
                    style={{
                      padding: '6px 12px',
                      background: 'rgba(246, 70, 93, 0.1)',
                      border: '1px solid var(--color-danger)',
                      borderRadius: '6px',
                      color: 'var(--color-danger)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                    }}
                  >
                    Stop
                  </button>
                </>
              ) : sessionData.status === 'paused' ? (
                <>
                  <button
                    onClick={() => controlSession('start')}
                    style={{
                      padding: '6px 12px',
                      background: 'rgba(14, 203, 129, 0.1)',
                      border: '1px solid var(--color-success)',
                      borderRadius: '6px',
                      color: 'var(--color-success)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                    }}
                  >
                    Resume
                  </button>
                  <button
                    onClick={() => controlSession('stop')}
                    style={{
                      padding: '6px 12px',
                      background: 'rgba(246, 70, 93, 0.1)',
                      border: '1px solid var(--color-danger)',
                      borderRadius: '6px',
                      color: 'var(--color-danger)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                    }}
                  >
                    Stop
                  </button>
                </>
              ) : null}

              <button
                onClick={deleteSession}
                style={{
                  padding: '6px 12px',
                  background: 'transparent',
                  border: '1px solid var(--border-primary)',
                  borderRadius: '6px',
                  color: 'var(--text-tertiary)',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textTransform: 'uppercase',
                }}
              >
                Delete
              </button>
            </div>
          </div>

          {/* Equity Curve Chart */}
          <Card className="chart-card" style={{ marginBottom: '20px' }}>
            <h2 style={{ marginBottom: '20px' }}>Real-Time Equity Curve</h2>
            {equityChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={equityChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
                    labelStyle={{ color: 'var(--color-binance)' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="equity"
                    name="Equity"
                    stroke="var(--color-binance)"
                    strokeWidth={3}
                    dot={false}
                    activeDot={{ r: 5, fill: 'var(--color-binance)', strokeWidth: 2, stroke: 'var(--bg-primary)' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="balance"
                    name="Balance"
                    stroke="var(--color-success)"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-tertiary)' }}>
                No equity data yet. Waiting for market updates...
              </div>
            )}
          </Card>

          {/* Price Chart */}
          {sessionData && (
            <Card>
              {/* Chart Controls */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                <h2>Price Chart</h2>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {/* Chart Type Toggle */}
                  <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-tertiary)', padding: '4px', borderRadius: '6px' }}>
                    <button
                      onClick={() => setChartType('tradingview')}
                      style={{
                        padding: '6px 12px',
                        background: chartType === 'tradingview' ? 'var(--color-binance)' : 'transparent',
                        color: chartType === 'tradingview' ? '#000' : 'var(--text-primary)',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: chartType === 'tradingview' ? 600 : 400,
                        transition: 'all 0.2s',
                      }}
                    >
                      TradingView
                    </button>
                    <button
                      onClick={() => setChartType('lightweight')}
                      style={{
                        padding: '6px 12px',
                        background: chartType === 'lightweight' ? 'var(--color-binance)' : 'transparent',
                        color: chartType === 'lightweight' ? '#000' : 'var(--text-primary)',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: chartType === 'lightweight' ? 600 : 400,
                        transition: 'all 0.2s',
                      }}
                    >
                      With Trades
                    </button>
                  </div>

                  {/* Interval Selector */}
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {['1m', '5m', '15m', '1h', '4h', '1d'].map((int) => (
                      <button
                        key={int}
                        onClick={() => setInterval(int)}
                        style={{
                          padding: '6px 12px',
                          background: interval === int ? 'var(--color-binance)' : 'var(--bg-tertiary)',
                          color: interval === int ? '#000' : 'var(--text-primary)',
                          border: interval === int ? 'none' : '1px solid var(--border-primary)',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px',
                          fontWeight: interval === int ? 600 : 400,
                          transition: 'all 0.2s',
                        }}
                      >
                        {int}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Chart Display */}
              {chartType === 'tradingview' ? (
                <TradingViewWidget
                  symbol={sessionData.symbol}
                  interval={interval}
                  theme="dark"
                  height={700}
                />
              ) : klineData.length > 0 ? (
                <ChartSection
                  klineData={klineData}
                  trades={recentTrades}
                  symbol={sessionData.symbol}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-tertiary)' }}>
                  No chart data available for {interval} interval
                </div>
              )}
            </Card>
          )}

          {/* Current Positions & Recent Trades */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            {/* Current Positions */}
            <Card>
              <h2 style={{ marginBottom: '20px' }}>Open Positions ({positions.length})</h2>
              {positions.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>Unreal. PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, idx) => (
                        <tr key={idx}>
                          <td>
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              background: pos.side === 'long' ? 'rgba(14, 203, 129, 0.1)' : 'rgba(246, 70, 93, 0.1)',
                              color: pos.side === 'long' ? 'var(--color-success)' : 'var(--color-danger)',
                            }}>
                              {pos.side?.toUpperCase()}
                            </span>
                          </td>
                          <td>{pos.quantity?.toFixed(4)}</td>
                          <td>{formatCurrency(pos.entry_price)}</td>
                          <td>{formatCurrency(pos.current_price)}</td>
                          <td style={{ color: (pos.unrealized_pnl || 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 600 }}>
                            {formatCurrency(pos.unrealized_pnl || 0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  No open positions
                </div>
              )}
            </Card>

            {/* Recent Trades */}
            <Card>
              <h2 style={{ marginBottom: '20px' }}>Recent Trades ({recentTrades.length})</h2>
              {recentTrades.length > 0 ? (
                <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Side</th>
                        <th>Price</th>
                        <th>PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentTrades.map((trade) => (
                        <tr key={trade.id}>
                          <td style={{ fontSize: '11px' }}>{formatDateTime(trade.timestamp)}</td>
                          <td>
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              background: trade.side === 'buy' ? 'rgba(14, 203, 129, 0.1)' : 'rgba(246, 70, 93, 0.1)',
                              color: trade.side === 'buy' ? 'var(--color-success)' : 'var(--color-danger)',
                            }}>
                              {trade.side.toUpperCase()}
                            </span>
                          </td>
                          <td>{trade.entry_price ? formatCurrency(trade.entry_price) : '-'}</td>
                          <td style={{ color: (trade.pnl || 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 600 }}>
                            {trade.pnl !== null ? formatCurrency(trade.pnl) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  No trades executed yet
                </div>
              )}
            </Card>
          </div>
        </>
      ) : (
        <Card>
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <h2 style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>No Session Selected</h2>
            <p style={{ color: 'var(--text-tertiary)', marginBottom: '30px' }}>
              Create a new paper trading session to start monitoring
            </p>
            <button onClick={() => setShowNewSessionModal(true)} className="btn-primary">
              + Create New Session
            </button>
          </div>
        </Card>
      )}

      {/* New Session Modal */}
      {showNewSessionModal && (
        <NewSessionModal
          onClose={() => setShowNewSessionModal(false)}
          onCreate={createNewSession}
        />
      )}

      {/* Pulse Animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.1);
          }
        }
      `}</style>
    </div>
  );
}

// New Session Modal Component
interface NewSessionModalProps {
  onClose: () => void;
  onCreate: (data: PaperTradingSessionCreate) => void;
}

function NewSessionModal({ onClose, onCreate }: NewSessionModalProps) {
  const [formData, setFormData] = useState<PaperTradingSessionCreate>({
    name: '',
    symbol: 'BTCUSDT',
    strategy: '',
    initial_capital: 10000,
    settings: {},
  });
  const [strategies, setStrategies] = useState<any[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOptions();
  }, []);

  const loadOptions = async () => {
    try {
      setLoading(true);
      const [strategiesRes, symbolsRes] = await Promise.all([
        apiClient.get('/strategies/available'),
        apiClient.get('/strategies/symbols'),
      ]);
      setStrategies(strategiesRes.data);
      setSymbols(symbolsRes.data);

      // Auto-select first strategy
      if (strategiesRes.data.length > 0) {
        const firstStrategy = strategiesRes.data[0];
        setFormData(prev => ({ ...prev, strategy: firstStrategy.strategy_name }));
        setSelectedStrategy(firstStrategy);
      }
    } catch (err) {
      console.error('Failed to load options:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStrategyChange = (strategyName: string) => {
    const strategy = strategies.find(s => s.strategy_name === strategyName);
    setSelectedStrategy(strategy);
    setFormData(prev => ({
      ...prev,
      strategy: strategyName,
      settings: {}, // Reset settings when strategy changes
    }));
  };

  const handleParameterChange = (paramName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      settings: {
        ...prev.settings,
        [paramName]: value,
      },
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
  };

  if (loading) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(4px)',
      }}>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(4px)',
      overflow: 'auto',
      padding: '20px',
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-primary)',
        borderRadius: '12px',
        padding: '32px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
      }}>
        <h2 style={{ marginBottom: '24px', color: 'var(--color-binance)' }}>
          Create New Paper Trading Session
        </h2>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Session Name (Optional)
            </label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="My Trading Session"
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Symbol *
            </label>
            <select
              value={formData.symbol}
              onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
              required
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                cursor: 'pointer',
              }}
            >
              {symbols.map(symbol => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Strategy *
            </label>
            <select
              value={formData.strategy}
              onChange={(e) => handleStrategyChange(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                cursor: 'pointer',
              }}
            >
              {strategies.map(strategy => (
                <option key={strategy.strategy_name} value={strategy.strategy_name}>
                  {strategy.display_name}
                </option>
              ))}
            </select>
            {selectedStrategy && selectedStrategy.description && (
              <p style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                {selectedStrategy.description}
              </p>
            )}
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary)' }}>
              Initial Capital *
            </label>
            <input
              type="number"
              value={formData.initial_capital}
              onChange={(e) => setFormData({ ...formData, initial_capital: Number(e.target.value) })}
              required
              min="100"
              step="100"
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            />
          </div>

          {/* Dynamic Strategy Parameters */}
          {selectedStrategy && selectedStrategy.parameter_schema && selectedStrategy.parameter_schema.length > 0 && (
            <div style={{
              marginBottom: '20px',
              padding: '16px',
              background: 'var(--bg-tertiary)',
              borderRadius: '8px',
              border: '1px solid var(--border-primary)',
            }}>
              <h3 style={{ marginBottom: '16px', fontSize: '14px', color: 'var(--text-primary)' }}>
                Strategy Parameters
              </h3>
              {selectedStrategy.parameter_schema.map((param: any) => (
                <div key={param.name} style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {param.name} {param.required && '*'}
                  </label>
                  {param.type === 'bool' ? (
                    <input
                      type="checkbox"
                      checked={formData.settings?.[param.name] ?? param.default}
                      onChange={(e) => handleParameterChange(param.name, e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                  ) : param.type === 'select' ? (
                    <select
                      value={formData.settings?.[param.name] ?? param.default}
                      onChange={(e) => handleParameterChange(param.name, e.target.value)}
                      required={param.required}
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '4px',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                      }}
                    >
                      {param.options?.map((opt: any) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={param.type === 'int' || param.type === 'float' ? 'number' : 'text'}
                      value={formData.settings?.[param.name] ?? param.default ?? ''}
                      onChange={(e) => handleParameterChange(
                        param.name,
                        param.type === 'int' ? parseInt(e.target.value) :
                        param.type === 'float' ? parseFloat(e.target.value) :
                        e.target.value
                      )}
                      required={param.required}
                      min={param.min}
                      max={param.max}
                      step={param.step || (param.type === 'int' ? 1 : 0.01)}
                      placeholder={param.default?.toString()}
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '4px',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                      }}
                    />
                  )}
                  {param.description && (
                    <p style={{ marginTop: '4px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                      {param.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
            >
              Create Session
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
