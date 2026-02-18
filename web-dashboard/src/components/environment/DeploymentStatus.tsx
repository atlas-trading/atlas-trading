import { useState, useEffect, useRef } from 'react';
import { environmentAPI } from '../../services/environmentApi';
import { useMetricsTSDB } from '../../hooks/useMetricsTSDB';
import type { ArgoDeploymentStatus } from '../../types/environment';

interface DeploymentHistoryEntry {
  timestamp: string;
  commit: string;
  status: 'success' | 'failed' | 'progressing';
  health: string;
  sync_status: string;
  api_server_image: string;
  web_dashboard_image: string;
}

export default function DeploymentStatus() {
  const [deployment, setDeployment] = useState<ArgoDeploymentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastCommitRef = useRef<string | null>(null);

  const { history, addEntry, clearHistory } = useMetricsTSDB<DeploymentHistoryEntry>('deployment-history');

  const fetchDeployment = async () => {
    try {
      const data = await environmentAPI.getDeploymentStatus();
      setDeployment(data);
      setError(null);
      setLoading(false);

      // 새 커밋이 감지되면 히스토리에 추가
      const commit = data.last_deployment.commit;
      if (commit && commit !== 'unknown' && commit !== lastCommitRef.current) {
        lastCommitRef.current = commit;
        addEntry({
          timestamp: data.last_deployment.time,
          commit,
          status: data.last_deployment.status,
          health: data.health,
          sync_status: data.sync_status,
          api_server_image: data.images.api_server,
          web_dashboard_image: data.images.web_dashboard,
        });
      }
    } catch (err) {
      setError('Failed to fetch deployment status. Backend may not be available.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployment();
    const interval = setInterval(fetchDeployment, 10000);
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'Healthy': return 'text-success';
      case 'Progressing': return 'text-warning';
      case 'Degraded': return 'text-danger';
      case 'Suspended': return 'text-muted';
      default: return 'text-secondary';
    }
  };

  const getSyncColor = (sync: string) => {
    switch (sync) {
      case 'Synced': return 'text-success';
      case 'OutOfSync': return 'text-warning';
      default: return 'text-secondary';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'success': return 'status-success';
      case 'failed': return 'status-danger';
      case 'progressing': return 'status-warning';
      default: return 'status-secondary';
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="text-secondary">Loading deployment status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="text-danger">{error}</p>
        <p className="text-muted">Ensure ArgoCD is accessible from the backend API.</p>
      </div>
    );
  }

  if (!deployment) return null;

  // 히스토리 역순 정렬 (최신이 위)
  const sortedHistory = [...history].reverse();

  return (
    <div className="environment-monitor">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Application Health</h2>
          </div>
          <div className="card-body">
            <div className="deployment-status-item">
              <span className="deployment-label">Health Status</span>
              <span className={`deployment-value ${getHealthColor(deployment.health)}`}>
                {deployment.health}
              </span>
            </div>
            <div className="deployment-status-item">
              <span className="deployment-label">Sync Status</span>
              <span className={`deployment-value ${getSyncColor(deployment.sync_status)}`}>
                {deployment.sync_status}
              </span>
            </div>
            <div className="deployment-status-item">
              <span className="deployment-label">Last Updated</span>
              <span className="deployment-value text-secondary">
                {new Date(deployment.last_deployment.time).toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Running Images</h2>
          </div>
          <div className="card-body">
            <div className="deployment-status-item">
              <span className="deployment-label">API Server</span>
              <span className="deployment-value text-primary" style={{ fontSize: '0.75rem', wordBreak: 'break-all' }}>
                {deployment.images.api_server}
              </span>
            </div>
            <div className="deployment-status-item">
              <span className="deployment-label">Web Dashboard</span>
              <span className="deployment-value text-primary" style={{ fontSize: '0.75rem', wordBreak: 'break-all' }}>
                {deployment.images.web_dashboard}
              </span>
            </div>
            <div className="deployment-status-item">
              <span className="deployment-label">Commit Hash</span>
              <span className="deployment-value font-mono text-secondary">
                {deployment.last_deployment.commit}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-8">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="card-title">
            Deployment History
            <span className="text-muted" style={{ fontSize: '0.8rem', fontWeight: 'normal', marginLeft: '8px' }}>
              ({sortedHistory.length}개 기록됨)
            </span>
          </h2>
          {sortedHistory.length > 0 && (
            <button
              onClick={clearHistory}
              style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                background: 'transparent',
                border: '1px solid var(--border-primary)',
                borderRadius: '4px',
                color: 'var(--text-tertiary)',
                cursor: 'pointer',
              }}
            >
              Clear
            </button>
          )}
        </div>
        <div className="card-body">
          {sortedHistory.length === 0 ? (
            <p className="text-muted" style={{ textAlign: 'center', padding: '16px' }}>
              배포 이벤트가 감지되면 여기에 자동으로 기록됩니다.
            </p>
          ) : (
            <div className="deployment-history">
              {sortedHistory.map((entry, idx) => (
                <div key={idx} className="deployment-history-item" style={{
                  borderBottom: idx < sortedHistory.length - 1 ? '1px solid var(--border-primary)' : 'none',
                  paddingBottom: '12px',
                  marginBottom: '12px',
                }}>
                  <div className="deployment-history-time" style={{ marginBottom: '4px' }}>
                    {new Date(entry.timestamp).toLocaleString()}
                  </div>
                  <div className="deployment-history-details" style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="deployment-history-commit font-mono" style={{ fontSize: '0.85rem' }}>
                      {entry.commit}
                    </span>
                    <span className={`deployment-history-status ${getStatusBadgeColor(entry.status)}`}>
                      {entry.status}
                    </span>
                    <span className={`text-secondary`} style={{ fontSize: '0.75rem' }}>
                      {entry.health} / {entry.sync_status}
                    </span>
                  </div>
                  <div style={{ marginTop: '4px', fontSize: '0.72rem', color: 'var(--text-tertiary)', wordBreak: 'break-all' }}>
                    {entry.api_server_image}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Health Check Legend</h2>
          </div>
          <div className="card-body">
            <div className="legend-list">
              <div className="legend-item">
                <span className="legend-dot bg-success"></span>
                <span className="legend-label">Healthy - All resources functioning normally</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot bg-warning"></span>
                <span className="legend-label">Progressing - Deployment in progress</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot bg-danger"></span>
                <span className="legend-label">Degraded - Some resources failing</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot bg-muted"></span>
                <span className="legend-label">Suspended - Application suspended</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Sync Status Legend</h2>
          </div>
          <div className="card-body">
            <div className="legend-list">
              <div className="legend-item">
                <span className="legend-dot bg-success"></span>
                <span className="legend-label">Synced - Git and cluster in sync</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot bg-warning"></span>
                <span className="legend-label">OutOfSync - Git ahead of cluster</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot bg-secondary"></span>
                <span className="legend-label">Unknown - Status unavailable</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
