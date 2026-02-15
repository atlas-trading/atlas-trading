// Cost Stress Test Panel - Critical for Strategy Validation
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { backtestAPI } from '../../services/api';
import type { CostStressResult } from '../../types/backtest';
import Card from '../common/Card';
import LoadingSpinner from '../common/LoadingSpinner';

interface CostStressPanelProps {
  backtestId: number;
}

export default function CostStressPanel({ backtestId }: CostStressPanelProps) {
  const [result, setResult] = useState<CostStressResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runTest = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await backtestAPI.runCostStressTest(backtestId);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cost stress test failed');
      console.error('Cost stress test error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getRiskColor = (grade: string) => {
    switch (grade) {
      case 'PASS': return 'var(--color-success)';
      case 'WARNING': return '#F0B90B';
      case 'FAIL': return 'var(--color-danger)';
      default: return 'var(--text-primary)';
    }
  };

  // Chart data for comparison
  const comparisonData = result ? [
    {
      name: 'Base',
      sharpe: result.base_sharpe,
      cagr: result.base_cagr,
      color: 'var(--color-binance)',
    },
    {
      name: 'Comm 2x',
      sharpe: result.comm_2x_sharpe,
      cagr: result.comm_2x_cagr,
      color: result.comm_2x_sharpe > 0.5 ? 'var(--color-success)' : 'var(--color-danger)',
    },
    {
      name: 'Slip +1tick',
      sharpe: result.slip_1tick_sharpe,
      cagr: result.slip_1tick_cagr,
      color: result.slip_1tick_cagr > 0 ? 'var(--color-success)' : 'var(--color-danger)',
    },
    {
      name: 'Delay 1bar',
      sharpe: result.delay_1bar_sharpe,
      cagr: result.delay_1bar_cagr,
      color: result.delay_1bar_total_return > 0 ? 'var(--color-success)' : 'var(--color-danger)',
    },
  ] : [];

  return (
    <Card>
      <h2 style={{ marginBottom: '20px', color: 'var(--color-binance)' }}>
        ⚠️ Cost Stress Test - Strategy Validation
      </h2>

      {!result ? (
        <div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px', fontSize: '14px' }}>
            <strong>Critical test for strategy validation.</strong> Tests robustness under realistic cost assumptions:
          </p>
          <ul style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px', paddingLeft: '20px' }}>
            <li><strong>Commission 2x:</strong> What if commission doubles?</li>
            <li><strong>Slippage +1 tick:</strong> What if you get 1 tick worse fill?</li>
            <li><strong>Execution Delay:</strong> What if orders execute 1 bar late?</li>
          </ul>
          <p style={{ color: 'var(--color-danger)', fontSize: '13px', marginBottom: '20px' }}>
            ⚠️ <strong>If strategy fails these tests, it should be discarded.</strong>
          </p>

          <button
            onClick={runTest}
            disabled={loading}
            className="btn-primary"
            style={{ padding: '10px 24px' }}
          >
            {loading ? 'Running Test...' : 'Run Cost Stress Test'}
          </button>

          {error && (
            <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(246, 70, 93, 0.1)', border: '1px solid var(--color-danger)', borderRadius: '6px', color: 'var(--color-danger)' }}>
              {error}
            </div>
          )}
        </div>
      ) : (
        <>
          {loading && <LoadingSpinner />}

          {/* Risk Grade */}
          <div style={{
            padding: '20px',
            background: 'var(--bg-tertiary)',
            borderRadius: '8px',
            marginBottom: '25px',
            border: `3px solid ${getRiskColor(result.risk_grade)}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '5px' }}>
                  Overall Risk Grade
                </div>
                <div style={{ fontSize: '36px', fontWeight: 700, color: getRiskColor(result.risk_grade) }}>
                  {result.risk_grade}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '5px' }}>
                  Test Result
                </div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: result.passes_stress_test ? 'var(--color-success)' : 'var(--color-danger)' }}>
                  {result.passes_stress_test ? 'PASSED' : 'FAILED'}
                </div>
              </div>
            </div>

            {result.failure_reasons.length > 0 && (
              <div style={{ marginTop: '15px', padding: '12px', background: 'rgba(246, 70, 93, 0.1)', borderRadius: '6px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '8px' }}>
                  Failure Reasons:
                </div>
                <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--color-danger)', fontSize: '13px' }}>
                  {result.failure_reasons.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Test 1: Commission 2x */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>
            Test 1: Commission 2x Impact
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Base Sharpe" value={result.base_sharpe.toFixed(2)} />
            <MetricItem label="2x Comm Sharpe" value={result.comm_2x_sharpe.toFixed(2)} valueColor={result.comm_2x_sharpe > 0.5 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="Sharpe Change" value={formatPercent(result.comm_2x_sharpe_delta_pct)} valueColor={result.comm_2x_sharpe_delta_pct > -50 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="2x Comm Return" value={formatPercent(result.comm_2x_total_return)} />
          </div>

          {/* Test 2: Slippage +1 tick */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>
            Test 2: Slippage +1 Tick Impact
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Base CAGR" value={formatPercent(result.base_cagr)} />
            <MetricItem label="Slippage CAGR" value={formatPercent(result.slip_1tick_cagr)} valueColor={result.slip_1tick_cagr > 0 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="CAGR Change" value={formatPercent(result.slip_1tick_cagr_delta_pct)} valueColor={result.slip_1tick_cagr_delta_pct > -80 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="Slip Return" value={formatPercent(result.slip_1tick_total_return)} />
          </div>

          {/* Test 3: Execution Delay */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>
            Test 3: Execution Delay (1 bar) Impact
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px', marginBottom: '25px' }}>
            <MetricItem label="Base Return" value={formatPercent(result.base_total_return)} />
            <MetricItem label="Delayed Return" value={formatPercent(result.delay_1bar_total_return)} valueColor={result.delay_1bar_total_return > 0 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="Return Change" value={formatPercent(result.delay_1bar_total_return_delta_pct)} valueColor={result.delay_1bar_total_return_delta_pct > -50 ? 'var(--color-success)' : 'var(--color-danger)'} />
            <MetricItem label="Delayed MDD" value={formatPercent(result.delay_1bar_max_drawdown)} valueColor="var(--color-danger)" />
          </div>

          {/* Comparison Chart */}
          <h3 style={{ fontSize: '14px', marginBottom: '15px', color: 'var(--text-secondary)' }}>
            Performance Comparison
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={comparisonData}>
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
                label={{ value: 'CAGR (%)', angle: -90, position: 'insideLeft', fill: 'var(--text-tertiary)' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                }}
              />
              <Bar dataKey="cagr" radius={[4, 4, 0, 0]}>
                {comparisonData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <button
            onClick={() => setResult(null)}
            className="btn-secondary"
            style={{ marginTop: '25px', padding: '8px 20px' }}
          >
            Run New Test
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
