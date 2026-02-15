// Monte Carlo Simulation Panel
import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { backtestAPI } from '../../services/api';
import type { MonteCarloResult } from '../../types/backtest';
import Card from '../common/Card';
import LoadingSpinner from '../common/LoadingSpinner';

interface MonteCarloPanelProps {
  backtestId: number;
  initialCapital: number;
}

export default function MonteCarloPanel({ backtestId, initialCapital }: MonteCarloPanelProps) {
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nSimulations, setNSimulations] = useState(1000);

  const runSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await backtestAPI.runMonteCarlo(backtestId, nSimulations);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Monte Carlo simulation failed');
      console.error('Monte Carlo error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Histogram 데이터 준비
  const histogramData = result ? (() => {
    if (!result.all_final_capitals || result.all_final_capitals.length === 0) {
      return [];
    }

    const capitals = [...result.all_final_capitals].sort((a, b) => a - b);
    const min = Math.min(...capitals);
    const max = Math.max(...capitals);

    // Handle case where all values are the same (std = 0)
    if (min === max) {
      return [{
        range: `${formatCurrency(min)}`,
        count: capitals.length,
        color: min < initialCapital ? 'var(--color-danger)' : 'var(--color-success)',
      }];
    }

    const binCount = 30;
    const binWidth = (max - min) / binCount;

    const bins = Array(binCount).fill(0).map((_, i) => ({
      start: min + i * binWidth,
      end: min + (i + 1) * binWidth,
      count: 0,
    }));

    capitals.forEach(capital => {
      const binIndex = Math.min(Math.floor((capital - min) / binWidth), binCount - 1);
      bins[binIndex].count++;
    });

    return bins.map(bin => ({
      range: `${formatCurrency(bin.start)}`,
      count: bin.count,
      color: bin.end < initialCapital ? 'var(--color-danger)' : 'var(--color-success)',
    }));
  })() : [];

  const getRiskColor = (grade: string) => {
    switch (grade) {
      case 'LOW': return 'var(--color-success)';
      case 'MEDIUM': return '#F0B90B';
      case 'HIGH': return 'var(--color-danger)';
      default: return 'var(--text-primary)';
    }
  };

  return (
    <Card>
      <h2 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>Monte Carlo Simulation</h2>

      {!result ? (
        <div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px', fontSize: '14px' }}>
            Validates strategy reliability by randomly shuffling trade order. <br />
            Answers the question: "Was the profit just luck?"
          </p>

          <div style={{ display: 'flex', gap: '15px', alignItems: 'center', marginBottom: '20px' }}>
            <label style={{ fontSize: '14px' }}>
              Simulation Count:
              <select
                value={nSimulations}
                onChange={(e) => setNSimulations(Number(e.target.value))}
                style={{
                  marginLeft: '10px',
                  padding: '8px 12px',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                }}
              >
                <option value={100}>100 (Fast)</option>
                <option value={500}>500</option>
                <option value={1000}>1,000 (Recommended)</option>
                <option value={5000}>5,000</option>
                <option value={10000}>10,000 (Slow)</option>
              </select>
            </label>

            <button
              onClick={runSimulation}
              disabled={loading}
              className="btn-primary"
              style={{ padding: '8px 20px' }}
            >
              {loading ? 'Running...' : 'Run Simulation'}
            </button>
          </div>

          {error && (
            <div style={{ padding: '15px', background: 'rgba(246, 70, 93, 0.1)', border: '1px solid var(--color-danger)', borderRadius: '6px', color: 'var(--color-danger)' }}>
              {error}
            </div>
          )}
        </div>
      ) : (
        <>
          {loading && <LoadingSpinner />}

          {/* 리스크 등급 */}
          <div style={{
            padding: '20px',
            background: 'var(--bg-tertiary)',
            borderRadius: '8px',
            marginBottom: '25px',
            border: `2px solid ${getRiskColor(result.risk_grade)}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '5px' }}>Risk Grade</div>
                <div style={{ fontSize: '32px', fontWeight: 700, color: getRiskColor(result.risk_grade) }}>
                  {result.risk_grade}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '5px' }}>Probability of Loss</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: result.probability_of_loss > 30 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                  {result.probability_of_loss.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Return Statistics */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Return Distribution</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Mean" value={formatPercent(result.total_return_mean)} />
            <MetricItem label="Median" value={formatPercent(result.total_return_median)} />
            <MetricItem label="Std Dev" value={formatPercent(result.total_return_std)} />
            <MetricItem label="5th Percentile" value={formatPercent(result.total_return_5th)} valueColor="var(--color-danger)" />
            <MetricItem label="95th Percentile" value={formatPercent(result.total_return_95th)} valueColor="var(--color-success)" />
          </div>

          {/* Slight Edge - Sample Wealth Paths */}
          {result.sample_equity_curves && result.sample_equity_curves.length > 0 && (() => {
            // Prepare data: merge all curves into single dataset
            const maxLength = Math.max(...result.sample_equity_curves.map(c => c.length));
            const chartData = Array.from({ length: maxLength }, (_, index) => {
              const point: any = { index };
              result.sample_equity_curves.slice(0, 10).forEach((curve, curveIdx) => {
                point[`path${curveIdx}`] = curve[index] ?? null;
              });
              return point;
            });

            // Calculate trend line using linear regression
            const calculateTrendLine = () => {
              // Average all paths to get mean wealth trajectory
              const meanPath = Array.from({ length: maxLength }, (_, index) => {
                const validValues = result.sample_equity_curves
                  .map(curve => curve[index])
                  .filter(v => v != null);
                return validValues.length > 0
                  ? validValues.reduce((sum, v) => sum + v, 0) / validValues.length
                  : null;
              });

              // Simple linear regression: y = mx + b
              const validPoints = meanPath
                .map((y, x) => ({ x, y }))
                .filter(p => p.y != null) as { x: number; y: number }[];

              if (validPoints.length < 2) return null;

              const n = validPoints.length;
              const sumX = validPoints.reduce((sum, p) => sum + p.x, 0);
              const sumY = validPoints.reduce((sum, p) => sum + p.y, 0);
              const sumXY = validPoints.reduce((sum, p) => sum + p.x * p.y, 0);
              const sumX2 = validPoints.reduce((sum, p) => sum + p.x * p.x, 0);

              const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
              const intercept = (sumY - slope * sumX) / n;

              return Array.from({ length: maxLength }, (_, x) => ({
                index: x,
                trend: slope * x + intercept,
              }));
            };

            const trendData = calculateTrendLine();

            const colors = [
              '#4A90E2', '#50C878', '#E94B3C', '#9B59B6', '#F39C12',
              '#16A085', '#E67E22', '#C0392B', '#2ECC71', '#3498DB'
            ];

            return (
              <>
                <h3 style={{ fontSize: '14px', marginBottom: '15px', marginTop: '25px', color: 'var(--text-secondary)' }}>
                  Sample Wealth Paths (Slight Edge Validation)
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '15px' }}>
                  Shows {Math.min(10, result.sample_equity_curves.length)} simulated wealth paths with trend line. Consistent upward trend = Strategy has edge. Random scatter = Pure luck.
                </p>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                    <XAxis
                      dataKey="index"
                      stroke="var(--text-tertiary)"
                      style={{ fontSize: 10 }}
                      tick={{ fill: 'var(--text-tertiary)' }}
                      label={{ value: 'Trades', position: 'insideBottom', offset: -5, fill: 'var(--text-tertiary)' }}
                    />
                    <YAxis
                      stroke="var(--text-tertiary)"
                      style={{ fontSize: 11 }}
                      tick={{ fill: 'var(--text-tertiary)' }}
                      label={{ value: 'Capital ($)', angle: -90, position: 'insideLeft', fill: 'var(--text-tertiary)' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-secondary)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '6px',
                        color: 'var(--text-primary)',
                      }}
                    />
                    {/* Individual wealth paths with lower opacity */}
                    {result.sample_equity_curves.slice(0, 10).map((_, idx) => (
                      <Line
                        key={idx}
                        type="monotone"
                        dataKey={`path${idx}`}
                        stroke={colors[idx % colors.length]}
                        strokeWidth={1}
                        dot={false}
                        opacity={0.3}
                        connectNulls={false}
                      />
                    ))}
                    {/* Trend line - bold and prominent */}
                    {trendData && (
                      <Line
                        type="monotone"
                        dataKey="trend"
                        data={trendData}
                        stroke="#F0B90B"
                        strokeWidth={3}
                        dot={false}
                        strokeDasharray="5 5"
                        opacity={1}
                        name="Trend"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </>
            );
          })()}

          {/* Final Capital Histogram */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', marginTop: '25px', color: 'var(--text-secondary)' }}>Final Capital Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={histogramData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis
                dataKey="range"
                stroke="var(--text-tertiary)"
                style={{ fontSize: 10 }}
                tick={{ fill: 'var(--text-tertiary)' }}
              />
              <YAxis
                stroke="var(--text-tertiary)"
                style={{ fontSize: 11 }}
                tick={{ fill: 'var(--text-tertiary)' }}
                label={{ value: 'Frequency', angle: -90, position: 'insideLeft', fill: 'var(--text-tertiary)' }}
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
                {histogramData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Risk Metrics */}
          <h3 style={{ fontSize: '14px', marginTop: '25px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Risk Metrics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem
              label="VaR (5%)"
              value={formatCurrency(result.value_at_risk_5)}
              tooltip="Expected loss in worst 5% cases"
              valueColor="var(--color-danger)"
            />
            <MetricItem
              label="CVaR (5%)"
              value={formatCurrency(result.conditional_var_5)}
              tooltip="Average loss in worst 5%"
              valueColor="var(--color-danger)"
            />
            <MetricItem
              label="Volatility Ratio"
              value={result.volatility_ratio.toFixed(3)}
              tooltip="Std Dev / Mean"
            />
            <MetricItem
              label="95% Confidence Interval"
              value={`${formatCurrency(result.confidence_interval_95[0])} ~ ${formatCurrency(result.confidence_interval_95[1])}`}
              tooltip="95% probability within this range"
            />
          </div>

          {/* MDD Statistics */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>Max Drawdown Distribution</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px' }}>
            <MetricItem label="Mean MDD" value={formatPercent(result.max_drawdown_mean)} />
            <MetricItem label="Median MDD" value={formatPercent(result.max_drawdown_median)} />
            <MetricItem label="Worst MDD" value={formatPercent(result.max_drawdown_worst)} valueColor="var(--color-danger)" />
            <MetricItem label="Best MDD" value={formatPercent(result.max_drawdown_best)} valueColor="var(--color-success)" />
          </div>

          <button
            onClick={() => setResult(null)}
            className="btn-secondary"
            style={{ marginTop: '25px', padding: '8px 20px' }}
          >
            New Simulation
          </button>
        </>
      )}
    </Card>
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
          fontSize: '18px',
          fontWeight: 700,
          color: valueColor || 'var(--text-primary)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
