import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, LineChart, Line } from 'recharts';
import { environmentAPI } from '../../services/environmentApi';
import type { InfrastructureMetrics } from '../../types/environment';
import { useMetricsTSDB } from '../../hooks/useMetricsTSDB';

interface MetricsSnapshot {
  timestamp: string;
  cpuPercent: number;
  memoryPercent: number;
}

export default function InfrastructureMonitor() {
  const [metrics, setMetrics] = useState<InfrastructureMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { history, addEntry, clearHistory } = useMetricsTSDB<MetricsSnapshot>('infra-metrics-tsdb');

  const fetchMetrics = async () => {
    try {
      const data = await environmentAPI.getInfraMetrics();
      setMetrics(data);
      setError(null);
      setLoading(false);
      const cpu = parseFloat(((data.cpu_usage / data.cpu_total) * 100).toFixed(1));
      const mem = parseFloat(((data.memory_usage / data.memory_total) * 100).toFixed(1));
      addEntry({
        timestamp: new Date().toISOString(),
        cpuPercent: cpu,
        memoryPercent: mem,
      });
    } catch (err) {
      setError('Failed to fetch infrastructure metrics. Backend may not be available.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="text-secondary">Loading infrastructure metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="text-danger">{error}</p>
        <p className="text-muted">Ensure the Kubernetes cluster is accessible from the backend API.</p>
      </div>
    );
  }

  if (!metrics) return null;

  const cpuPercent = ((metrics.cpu_usage / metrics.cpu_total) * 100).toFixed(1);
  const memoryPercent = ((metrics.memory_usage / metrics.memory_total) * 100).toFixed(1);

  // Prepare deployment status data for chart
  const deploymentData = metrics.deployments.map(dep => ({
    name: dep.name,
    replicas: dep.replicas,
    ready: dep.ready_replicas,
  }));

  return (
    <div className="environment-monitor">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="metric-card">
          <div className="metric-icon normal">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <div className="metric-label">Nodes</div>
          <div className="metric-value">{metrics.nodes_ready} / {metrics.nodes_total}</div>
          <div className={`metric-status ${metrics.nodes_ready === metrics.nodes_total ? 'normal' : 'warning'}`}>
            {metrics.nodes_ready === metrics.nodes_total ? 'All Ready' : 'Some Offline'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon normal">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <div className="metric-label">Pods</div>
          <div className="metric-value">{metrics.pods_running} / {metrics.pods_total}</div>
          <div className={`metric-status ${metrics.pods_running === metrics.pods_total ? 'normal' : 'warning'}`}>
            {metrics.pods_running === metrics.pods_total ? 'All Running' : 'Some Pending'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon power">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
          <div className="metric-label">CPU Usage</div>
          <div className="metric-value">{cpuPercent}%</div>
          <div className={`metric-status ${parseFloat(cpuPercent) > 80 ? 'warning' : 'normal'}`}>
            {parseFloat(cpuPercent) > 80 ? 'High' : 'Normal'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon temperature">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
          </div>
          <div className="metric-label">Memory Usage</div>
          <div className="metric-value">{memoryPercent}%</div>
          <div className={`metric-status ${parseFloat(memoryPercent) > 80 ? 'warning' : 'normal'}`}>
            {parseFloat(memoryPercent) > 80 ? 'High' : 'Normal'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Cluster Resources</h2>
          </div>
          <div className="card-body">
            <div className="resource-section mb-6">
              <div className="resource-info mb-2">
                <span className="resource-label">CPU</span>
                <span className="resource-value">{metrics.cpu_usage.toFixed(2)} / {metrics.cpu_total.toFixed(2)} cores</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${cpuPercent}%`,
                    backgroundColor: parseFloat(cpuPercent) > 80 ? '#F6465D' : '#0ECB81'
                  }}
                ></div>
              </div>
              <div className="resource-percent">{cpuPercent}%</div>
            </div>

            <div className="resource-section">
              <div className="resource-info mb-2">
                <span className="resource-label">Memory</span>
                <span className="resource-value">
                  {(metrics.memory_usage / 1024 / 1024 / 1024).toFixed(2)} / {(metrics.memory_total / 1024 / 1024 / 1024).toFixed(2)} GB
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${memoryPercent}%`,
                    backgroundColor: parseFloat(memoryPercent) > 80 ? '#F6465D' : '#0ECB81'
                  }}
                ></div>
              </div>
              <div className="resource-percent">{memoryPercent}%</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Deployment Status</h2>
          </div>
          <div className="card-body">
            <div className="deployments-list">
              {metrics.deployments.map((dep, idx) => (
                <div key={idx} className="deployment-item">
                  <div className="deployment-header">
                    <span className="deployment-name">{dep.name}</span>
                    <span className={`deployment-status ${dep.available ? 'status-ready' : 'status-warning'}`}>
                      {dep.available ? '✓ Available' : '⚠ Unavailable'}
                    </span>
                  </div>
                  <div className="deployment-details">
                    <span className="text-muted">Namespace: {dep.namespace}</span>
                    <span className="text-muted">
                      Replicas: {dep.ready_replicas}/{dep.replicas}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {deploymentData.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Deployment Replicas</h2>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={deploymentData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="name" stroke="var(--text-tertiary)" />
                <YAxis stroke="var(--text-tertiary)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Bar dataKey="replicas" fill="#848E9C" name="Desired" />
                <Bar dataKey="ready" fill="#0ECB81" name="Ready" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {history.length > 0 && (() => {
        const recentHistory = history.slice(-20);
        const chartData = recentHistory.map(entry => ({
          time: new Date(entry.timestamp).toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
          }),
          cpu: entry.cpuPercent,
          memory: entry.memoryPercent,
        }));
        const firstTs = new Date(recentHistory[0].timestamp);
        const lastTs = new Date(recentHistory[recentHistory.length - 1].timestamp);
        const diffMinutes = Math.round((lastTs.getTime() - firstTs.getTime()) / 60000);

        return (
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2 className="card-title">Resource Usage History</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span className="text-muted" style={{ fontSize: '0.875rem' }}>
                  {diffMinutes > 0 ? `지난 ${diffMinutes}분` : '최근'} 데이터 ({recentHistory.length}포인트)
                </span>
                <button
                  onClick={clearHistory}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'transparent',
                    border: '1px solid var(--border-primary)',
                    borderRadius: '4px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis
                    dataKey="time"
                    stroke="var(--text-tertiary)"
                    tick={{ fontSize: 11 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="var(--text-tertiary)"
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number, name: string) => [
                      `${value}%`,
                      name === 'cpu' ? 'CPU Usage' : 'Memory Usage',
                    ]}
                  />
                  <Legend
                    formatter={(value) => value === 'cpu' ? 'CPU Usage %' : 'Memory Usage %'}
                  />
                  <Line
                    type="monotone"
                    dataKey="cpu"
                    stroke="#F0B90B"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    stroke="#0ECB81"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
