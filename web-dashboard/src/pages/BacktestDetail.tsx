// Backtest detail page - Single scroll view
import { useParams, useNavigate } from 'react-router-dom';
import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useBacktestFull } from '../hooks/useBacktest';
import Card from '../components/common/Card';
import StatCard from '../components/common/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EquityCurveChart from '../components/charts/EquityCurveChart';
import DrawdownChart from '../components/charts/DrawdownChart';
import RollingSharpeChart from '../components/charts/RollingSharpeChart';
import HoldingTimeScatterChart from '../components/charts/HoldingTimeScatterChart';
import MonteCarloPanel from '../components/backtest/MonteCarloPanel';
import CostStressPanel from '../components/backtest/CostStressPanel';

export default function BacktestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, loading, error } = useBacktestFull(id!);

  // 고급 지표 계산 (클라이언트 사이드)
  const advancedMetrics = useMemo(() => {
    if (!data || !data.trades.length) return null;

    const trades = data.trades;
    const winningTrades = trades.filter(t => (t.pnl ?? 0) > 0);
    const losingTrades = trades.filter(t => (t.pnl ?? 0) < 0);

    const totalProfit = winningTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0);
    const totalLoss = Math.abs(losingTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0));
    const netProfit = trades.reduce((sum, t) => sum + (t.pnl ?? 0), 0);

    const profitFactor = totalLoss > 0 ? totalProfit / totalLoss : totalProfit > 0 ? Infinity : 0;
    const expectancy = netProfit / trades.length;
    const avgWin = winningTrades.length > 0 ? totalProfit / winningTrades.length : 0;
    const avgLoss = losingTrades.length > 0 ? totalLoss / losingTrades.length : 0;
    const winLossRatio = avgLoss > 0 ? avgWin / avgLoss : avgWin > 0 ? Infinity : 0;

    // 연속 승/패
    let maxConsecWins = 0, maxConsecLosses = 0;
    let currentWins = 0, currentLosses = 0;
    trades.forEach(t => {
      if ((t.pnl ?? 0) > 0) {
        currentWins++;
        currentLosses = 0;
        maxConsecWins = Math.max(maxConsecWins, currentWins);
      } else if ((t.pnl ?? 0) < 0) {
        currentLosses++;
        currentWins = 0;
        maxConsecLosses = Math.max(maxConsecLosses, currentLosses);
      }
    });

    const totalCommission = trades.reduce((sum, t) => sum + (t.commission_paid ?? 0), 0);

    // Profit Concentration - 상위 5% 거래가 전체 수익에서 차지하는 비율
    const sortedPnls = [...trades].sort((a, b) => (b.pnl ?? 0) - (a.pnl ?? 0));
    const top5PercentCount = Math.max(1, Math.ceil(trades.length * 0.05));
    const top5PercentPnl = sortedPnls.slice(0, top5PercentCount).reduce((sum, t) => sum + (t.pnl ?? 0), 0);
    const profitConcentration = netProfit > 0 ? (top5PercentPnl / netProfit) * 100 : 0;

    return {
      profitFactor,
      expectancy,
      winLossRatio,
      maxConsecWins,
      maxConsecLosses,
      netProfit,
      netProfitPct: (netProfit / data.initial_capital) * 100,
      totalCommission,
      avgWin,
      avgLoss,
      profitConcentration,
      top5PercentCount,
      top5PercentPnl,
    };
  }, [data]);

  // 거래 분석 (클라이언트 사이드)
  const tradeAnalysis = useMemo(() => {
    if (!data || !data.trades.length) return null;

    const trades = data.trades;
    const pnls = trades.map(t => t.pnl ?? 0);

    // 보유 기간 계산
    const holdingPeriods = trades
      .filter(t => t.exit_time)
      .map(t => {
        const entry = new Date(t.entry_time).getTime();
        const exit = new Date(t.exit_time!).getTime();
        return (exit - entry) / (1000 * 60 * 60); // 시간
      });

    const avgHolding = holdingPeriods.length > 0 ? holdingPeriods.reduce((a, b) => a + b, 0) / holdingPeriods.length : 0;
    const medianHolding = holdingPeriods.length > 0 ? holdingPeriods.sort((a, b) => a - b)[Math.floor(holdingPeriods.length / 2)] : 0;

    // 손익 분포
    const largestWin = Math.max(...pnls, 0);
    const largestLoss = Math.min(...pnls, 0);
    const avgPnl = pnls.reduce((a, b) => a + b, 0) / pnls.length;

    // 거래 크기별 분류
    const smallWins = trades.filter(t => (t.pnl_pct ?? 0) > 0 && (t.pnl_pct ?? 0) < 1).length;
    const mediumWins = trades.filter(t => (t.pnl_pct ?? 0) >= 1 && (t.pnl_pct ?? 0) < 5).length;
    const largeWins = trades.filter(t => (t.pnl_pct ?? 0) >= 5).length;
    const smallLosses = trades.filter(t => (t.pnl_pct ?? 0) < 0 && (t.pnl_pct ?? 0) > -1).length;
    const mediumLosses = trades.filter(t => (t.pnl_pct ?? 0) <= -1 && (t.pnl_pct ?? 0) > -5).length;
    const largeLosses = trades.filter(t => (t.pnl_pct ?? 0) <= -5).length;

    return {
      avgHolding,
      medianHolding,
      largestWin,
      largestLoss,
      avgPnl,
      smallWins,
      mediumWins,
      largeWins,
      smallLosses,
      mediumLosses,
      largeLosses,
    };
  }, [data]);

  // Trade distribution chart data
  const distributionData = useMemo(() => {
    if (!tradeAnalysis) return [];
    return [
      { name: 'Small Win', count: tradeAnalysis.smallWins, color: 'rgba(14, 203, 129, 0.6)' },
      { name: 'Medium Win', count: tradeAnalysis.mediumWins, color: 'rgba(14, 203, 129, 0.8)' },
      { name: 'Large Win', count: tradeAnalysis.largeWins, color: 'var(--color-success)' },
      { name: 'Small Loss', count: tradeAnalysis.smallLosses, color: 'rgba(246, 70, 93, 0.6)' },
      { name: 'Medium Loss', count: tradeAnalysis.mediumLosses, color: 'rgba(246, 70, 93, 0.8)' },
      { name: 'Large Loss', count: tradeAnalysis.largeLosses, color: 'var(--color-danger)' },
    ];
  }, [tradeAnalysis]);

  if (loading) {
    return <LoadingSpinner fullScreen />;
  }

  if (error || !data) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--color-danger)' }}>⚠️ Error</h2>
        <p style={{ color: 'var(--text-secondary)' }}>{error || 'Data not found.'}</p>
        <button onClick={() => navigate('/backtests')} className="btn-primary" style={{ marginTop: '20px' }}>
          Back to List
        </button>
      </div>
    );
  }

  const formatPercent = (value: number | null) => {
    if (value === null) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return '-';
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}.${date.getDate()}.${date.getFullYear()}`;
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}.${date.getDate()}.${date.getFullYear()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  };

  // Calculate CAGR and Calmar Ratio
  const calculateCAGR = () => {
    if (!data.total_return || !data.start_date || !data.end_date) return null;

    const startDate = new Date(data.start_date);
    const endDate = new Date(data.end_date);
    const days = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
    const years = days / 365.25;

    if (years <= 0) return null;

    const finalValue = 1 + (data.total_return / 100);
    if (finalValue <= 0) return null;

    const cagr = (Math.pow(finalValue, 1 / years) - 1) * 100;
    return cagr;
  };

  const cagr = calculateCAGR();
  const calmarRatio = (cagr !== null && data.max_drawdown && Math.abs(data.max_drawdown) > 0)
    ? cagr / Math.abs(data.max_drawdown)
    : null;

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '30px' }}>
        <button
          onClick={() => navigate('/backtests')}
          className="btn-secondary"
          style={{ marginBottom: '20px' }}
        >
          ← Back to List
        </button>
        <h1>
          {data.strategy_name} - {data.symbol}
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          {formatDate(data.start_date)} ~ {formatDate(data.end_date)} | {data.timeframe}
        </p>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '30px' }}>
        <StatCard label="Total Return" value={formatPercent(data.total_return)} />
        <StatCard label="CAGR" value={cagr !== null ? formatPercent(cagr) : '-'} />
        <StatCard label="Final Capital" value={formatCurrency(data.final_capital)} />
        <StatCard label="Max Drawdown" value={formatPercent(data.max_drawdown)} />
        <StatCard label="Sharpe Ratio" value={data.sharpe_ratio?.toFixed(2) ?? '-'} />
        <StatCard
          label="Calmar Ratio"
          value={calmarRatio !== null ? calmarRatio.toFixed(2) : '-'}
                 />
        <StatCard label="Total Trades" value={data.total_trades ?? 0} />
        <StatCard
          label="Win Rate"
          value={data.win_rate !== null ? `${data.win_rate.toFixed(1)}%` : '-'}
        />
      </div>

      {/* Profit Concentration Warning */}
      {advancedMetrics && advancedMetrics.profitConcentration > 80 && (
        <div style={{
          padding: '15px 20px',
          background: 'rgba(246, 70, 93, 0.1)',
          border: '2px solid var(--color-danger)',
          borderRadius: '8px',
          marginBottom: '30px',
          display: 'flex',
          alignItems: 'center',
          gap: '15px'
        }}>
          <span style={{ fontSize: '32px' }}>⚠️</span>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--color-danger)', marginBottom: '5px' }}>
              High Tail Risk Dependency Detected
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Top {advancedMetrics.top5PercentCount} trades ({(advancedMetrics.top5PercentCount / data.total_trades! * 100).toFixed(1)}%)
              contribute <strong style={{ color: 'var(--color-danger)' }}>{advancedMetrics.profitConcentration.toFixed(1)}%</strong> of total profit.
              This strategy heavily depends on a few large wins (tail risk).
            </div>
          </div>
        </div>
      )}

      {advancedMetrics && advancedMetrics.profitConcentration <= 80 && advancedMetrics.profitConcentration > 0 && (
        <div style={{
          padding: '15px 20px',
          background: 'rgba(14, 203, 129, 0.1)',
          border: '2px solid var(--color-success)',
          borderRadius: '8px',
          marginBottom: '30px',
          display: 'flex',
          alignItems: 'center',
          gap: '15px'
        }}>
          <span style={{ fontSize: '32px' }}>✓</span>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--color-success)', marginBottom: '5px' }}>
              Good Profit Distribution
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Top {advancedMetrics.top5PercentCount} trades contribute {advancedMetrics.profitConcentration.toFixed(1)}% of total profit.
              Profits are well-distributed across trades (low tail risk dependency).
            </div>
          </div>
        </div>
      )}

      {/* Equity Curve */}
      <Card className="chart-card" style={{ marginBottom: '20px' }}>
        <h2>Equity Curve</h2>
        <EquityCurveChart data={data.equity_curve} initialCapital={data.initial_capital} />
      </Card>

      {/* Drawdown Chart */}
      <Card className="chart-card" style={{ marginBottom: '20px' }}>
        <h2>Drawdown Analysis</h2>
        <DrawdownChart equityCurve={data.equity_curve} />
      </Card>

      {/* Rolling Sharpe Chart */}
      <Card className="chart-card" style={{ marginBottom: '20px' }}>
        <h2>Rolling Sharpe Ratio (90-day)</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '15px' }}>
          Detects regime collapse points. Sharp drops indicate strategy degradation or market regime shifts.
        </p>
        <RollingSharpeChart equityCurve={data.equity_curve} windowDays={90} />
      </Card>

      {/* Advanced Metrics */}
      {advancedMetrics && (
        <Card style={{ marginBottom: '20px' }}>
          <h2 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Advanced Performance Metrics</h2>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Profitability Metrics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem
              label="Profit Factor"
              value={advancedMetrics.profitFactor === Infinity ? '∞' : advancedMetrics.profitFactor.toFixed(2)}
              tooltip="Total Profit / Total Loss (>1 is profitable)"
              valueColor={advancedMetrics.profitFactor > 1 ? 'var(--color-success)' : 'var(--color-danger)'}
            />
            <MetricItem
              label="Expectancy"
              value={formatCurrency(advancedMetrics.expectancy)}
              tooltip="Average profit per trade"
              valueColor={advancedMetrics.expectancy > 0 ? 'var(--color-success)' : 'var(--color-danger)'}
            />
            <MetricItem
              label="Win/Loss Ratio"
              value={advancedMetrics.winLossRatio === Infinity ? '∞' : advancedMetrics.winLossRatio.toFixed(2)}
              tooltip="Average Win Size / Average Loss Size"
            />
            <MetricItem
              label="Net Profit"
              value={formatCurrency(advancedMetrics.netProfit)}
              tooltip="Total Net Profit"
              valueColor={advancedMetrics.netProfit > 0 ? 'var(--color-success)' : 'var(--color-danger)'}
            />
          </div>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Trade Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
            <MetricItem label="Max Consecutive Wins" value={advancedMetrics.maxConsecWins} />
            <MetricItem label="Max Consecutive Losses" value={advancedMetrics.maxConsecLosses} />
            <MetricItem label="Total Commission" value={formatCurrency(advancedMetrics.totalCommission)} />
            <MetricItem label="Average Win" value={formatCurrency(advancedMetrics.avgWin)} valueColor="var(--color-success)" />
            <MetricItem label="Average Loss" value={formatCurrency(advancedMetrics.avgLoss)} valueColor="var(--color-danger)" />
          </div>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Risk Concentration</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <MetricItem
              label="Profit Concentration"
              value={`${advancedMetrics.profitConcentration.toFixed(1)}%`}
              tooltip={`Top ${advancedMetrics.top5PercentCount} trades (5%) contribution to total profit`}
              valueColor={advancedMetrics.profitConcentration > 80 ? 'var(--color-danger)' : 'var(--color-success)'}
            />
            <MetricItem
              label="Top 5% Trades"
              value={advancedMetrics.top5PercentCount}
              tooltip="Number of trades in top 5%"
            />
            <MetricItem
              label="Top 5% PnL"
              value={formatCurrency(advancedMetrics.top5PercentPnl)}
              tooltip="Total PnL from top 5% trades"
              valueColor="var(--color-success)"
            />
          </div>
        </Card>
      )}

      {/* Trade Analysis */}
      {tradeAnalysis && (
        <Card style={{ marginBottom: '20px' }}>
          <h2 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Trade Analysis</h2>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Holding Period</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Average Holding Time" value={`${tradeAnalysis.avgHolding.toFixed(1)}h`} />
            <MetricItem label="Median Holding Time" value={`${tradeAnalysis.medianHolding.toFixed(1)}h`} />
          </div>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>PnL Distribution</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Average PnL" value={formatCurrency(tradeAnalysis.avgPnl)} valueColor={tradeAnalysis.avgPnl >= 0 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="Largest Win" value={formatCurrency(tradeAnalysis.largestWin)} valueColor="var(--color-success)" />
            <MetricItem label="Largest Loss" value={formatCurrency(tradeAnalysis.largestLoss)} valueColor="var(--color-danger)" />
          </div>

          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Trade Size Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={distributionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis
                dataKey="name"
                stroke="var(--text-tertiary)"
                style={{ fontSize: 11 }}
                tick={{ fill: 'var(--text-tertiary)' }}
              />
              <YAxis
                stroke="var(--text-tertiary)"
                style={{ fontSize: 11 }}
                tick={{ fill: 'var(--text-tertiary)' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {distributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
            Small: 0-1%, Medium: 1-5%, Large: 5%+
          </div>

          <h3 style={{ fontSize: '14px', marginTop: '25px', marginBottom: '15px', color: 'var(--text-secondary)' }}>
            Holding Time vs PnL
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '15px' }}>
            Scatter plot showing relationship between holding time and profit/loss. Identifies optimal holding periods.
          </p>
          <HoldingTimeScatterChart trades={data.trades} />
        </Card>
      )}

      {/* Cost Stress Test */}
      <div style={{ marginBottom: '20px' }}>
        <CostStressPanel backtestId={data.id} />
      </div>

      {/* Monte Carlo Simulation */}
      <div style={{ marginBottom: '20px' }}>
        <MonteCarloPanel backtestId={data.id} initialCapital={data.initial_capital} />
      </div>

      {/* Trades Table */}
      <Card>
        <h2>Trade History ({data.trades.length})</h2>
        <div style={{ overflowX: 'auto', marginTop: '20px' }}>
          <table>
            <thead>
              <tr>
                <th>Entry Time</th>
                <th>Exit Time</th>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Quantity</th>
                <th>PnL</th>
                <th>PnL %</th>
                <th>Commission</th>
              </tr>
            </thead>
            <tbody>
              {data.trades.map((trade) => (
                <tr key={trade.id}>
                  <td style={{ fontSize: '12px' }}>
                    {formatDateTime(trade.entry_time)}
                  </td>
                  <td style={{ fontSize: '12px' }}>
                    {trade.exit_time ? formatDateTime(trade.exit_time) : '-'}
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        background: trade.side === 'long' ? 'rgba(14, 203, 129, 0.1)' : 'rgba(246, 70, 93, 0.1)',
                        color: trade.side === 'long' ? 'var(--color-success)' : 'var(--color-danger)',
                      }}
                    >
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  <td>{formatCurrency(trade.entry_price)}</td>
                  <td>{trade.exit_price ? formatCurrency(trade.exit_price) : '-'}</td>
                  <td>{trade.quantity.toFixed(4)}</td>
                  <td style={{ color: (trade.pnl ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    {trade.pnl !== null ? formatCurrency(trade.pnl) : '-'}
                  </td>
                  <td style={{ color: (trade.pnl_pct ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    {trade.pnl_pct !== null ? formatPercent(trade.pnl_pct) : '-'}
                  </td>
                  <td style={{ color: 'var(--text-tertiary)' }}>
                    {trade.commission_paid ? formatCurrency(trade.commission_paid) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

interface MetricItemProps {
  label: string;
  value: string | number;
  tooltip?: string;
  valueColor?: string;
}

function MetricItem({ label, value, tooltip, valueColor }: MetricItemProps) {
  return (
    <div
      style={{
        padding: '12px 15px',
        background: 'var(--bg-tertiary)',
        borderRadius: '6px',
        border: '1px solid var(--border-primary)',
      }}
    >
      <div
        style={{
          fontSize: '10px',
          color: 'var(--text-tertiary)',
          marginBottom: '6px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
        title={tooltip}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: '20px',
          fontWeight: 700,
          color: valueColor || 'var(--text-primary)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
