import { useState, useEffect } from 'react';
import { environmentAPI } from '../../services/environmentApi';
import type { ArgoDeploymentStatus } from '../../types/environment';

export default function DeploymentStatus() {
  const [deployment, setDeployment] = useState<ArgoDeploymentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDeployment = async () => {
    try {
      const data = await environmentAPI.getDeploymentStatus();
      setDeployment(data);
      setError(null);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch deployment status. Backend may not be available.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployment();
    const interval = setInterval(fetchDeployment, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

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

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'Healthy':
        return 'text-success';
      case 'Progressing':
        return 'text-warning';
      case 'Degraded':
        return 'text-danger';
      case 'Suspended':
        return 'text-muted';
      default:
        return 'text-secondary';
    }
  };

  const getSyncColor = (sync: string) => {
    switch (sync) {
      case 'Synced':
        return 'text-success';
      case 'OutOfSync':
        return 'text-warning';
      default:
        return 'text-secondary';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'status-success';
      case 'failed':
        return 'status-danger';
      case 'progressing':
        return 'status-warning';
      default:
        return 'status-secondary';
    }
  };

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
              <span className="deployment-value text-primary">
                {deployment.images.api_server}
              </span>
            </div>
            <div className="deployment-status-item">
              <span className="deployment-label">Web Dashboard</span>
              <span className="deployment-value text-primary">
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

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Deployment History</h2>
        </div>
        <div className="card-body">
          <div className="deployment-history">
            <div className="deployment-history-item">
              <div className="deployment-history-time">
                {new Date(deployment.last_deployment.time).toLocaleString()}
              </div>
              <div className="deployment-history-details">
                <span className="deployment-history-commit font-mono">
                  {deployment.last_deployment.commit}
                </span>
                <span className={`deployment-history-status ${getStatusBadgeColor(deployment.last_deployment.status)}`}>
                  {deployment.last_deployment.status}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
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
