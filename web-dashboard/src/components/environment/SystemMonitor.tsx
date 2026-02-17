import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { environmentAPI } from '../../services/environmentApi';
import type { SystemMetrics } from '../../types/environment';

interface ChartDataPoint {
  timestamp: string;
  cpu_temp: number;
  gpu_temp: number;
  cpu_power: number;
  gpu_power: number;
  memory_percent: number;
  disk_percent: number;
}

export default function SystemMonitor() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      const data = await environmentAPI.getSystemMetrics();
      setMetrics(data);
      setError(null);

      // Add to chart data (keep last 20 points)
      const newPoint: ChartDataPoint = {
        timestamp: new Date(data.timestamp).toLocaleTimeString(),
        cpu_temp: data.cpu_temp,
        gpu_temp: data.gpu_temp,
        cpu_power: data.cpu_power,
        gpu_power: data.gpu_power,
        memory_percent: (data.memory_used / data.memory_total) * 100,
        disk_percent: (data.disk_used / data.disk_total) * 100,
      };

      setChartData((prev) => {
        const updated = [...prev, newPoint];
        return updated.slice(-20); // Keep last 20 points
      });

      setLoading(false);
    } catch (err) {
      setError('Failed to fetch system metrics. Backend may not be available.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="text-secondary">Loading system metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="text-danger">{error}</p>
        <p className="text-muted">Ensure the backend API is running at the configured endpoint.</p>
      </div>
    );
  }

  if (!metrics) return null;

  const memoryPercent = ((metrics.memory_used / metrics.memory_total) * 100).toFixed(1);
  const diskPercent = ((metrics.disk_used / metrics.disk_total) * 100).toFixed(1);

  return (
    <div className="environment-monitor">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="metric-card">
          <div className="metric-icon temperature">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div className="metric-label">CPU Temperature</div>
          <div className="metric-value">{metrics.cpu_temp.toFixed(1)}°C</div>
          <div className={`metric-status ${metrics.cpu_temp > 80 ? 'warning' : 'normal'}`}>
            {metrics.cpu_temp > 80 ? 'High' : 'Normal'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon temperature">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div className="metric-label">GPU Temperature</div>
          <div className="metric-value">{metrics.gpu_temp.toFixed(1)}°C</div>
          <div className={`metric-status ${metrics.gpu_temp > 80 ? 'warning' : 'normal'}`}>
            {metrics.gpu_temp > 80 ? 'High' : 'Normal'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon power">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="metric-label">CPU Power</div>
          <div className="metric-value">{metrics.cpu_power.toFixed(1)}W</div>
          <div className="metric-status normal">Active</div>
        </div>

        <div className="metric-card">
          <div className="metric-icon power">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="metric-label">GPU Power</div>
          <div className="metric-value">{metrics.gpu_power.toFixed(1)}W</div>
          <div className="metric-status normal">Active</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Memory Usage</h2>
          </div>
          <div className="card-body">
            <div className="resource-usage">
              <div className="resource-info">
                <span className="resource-label">Used</span>
                <span className="resource-value">{(metrics.memory_used / 1024 / 1024 / 1024).toFixed(2)} GB</span>
              </div>
              <div className="resource-info">
                <span className="resource-label">Total</span>
                <span className="resource-value">{(metrics.memory_total / 1024 / 1024 / 1024).toFixed(2)} GB</span>
              </div>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${memoryPercent}%` }}
              ></div>
            </div>
            <div className="resource-percent">{memoryPercent}%</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Disk Usage</h2>
          </div>
          <div className="card-body">
            <div className="resource-usage">
              <div className="resource-info">
                <span className="resource-label">Used</span>
                <span className="resource-value">{(metrics.disk_used / 1024 / 1024 / 1024).toFixed(2)} GB</span>
              </div>
              <div className="resource-info">
                <span className="resource-label">Total</span>
                <span className="resource-value">{(metrics.disk_total / 1024 / 1024 / 1024).toFixed(2)} GB</span>
              </div>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${diskPercent}%` }}
              ></div>
            </div>
            <div className="resource-percent">{diskPercent}%</div>
          </div>
        </div>
      </div>

      {chartData.length > 0 && (
        <>
          <div className="card mb-6">
            <div className="card-header">
              <h2 className="card-title">Temperature Trends</h2>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="timestamp" stroke="var(--text-tertiary)" />
                  <YAxis stroke="var(--text-tertiary)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="cpu_temp"
                    stroke="#F0B90B"
                    name="CPU Temp (°C)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="gpu_temp"
                    stroke="#F6465D"
                    name="GPU Temp (°C)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Power Consumption</h2>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="timestamp" stroke="var(--text-tertiary)" />
                  <YAxis stroke="var(--text-tertiary)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="cpu_power"
                    stroke="#0ECB81"
                    name="CPU Power (W)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="gpu_power"
                    stroke="#848E9C"
                    name="GPU Power (W)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
