import { useState } from 'react';
import SystemMonitor from '../components/environment/SystemMonitor';
import InfrastructureMonitor from '../components/environment/InfrastructureMonitor';
import DeploymentStatus from '../components/environment/DeploymentStatus';

type TabType = 'system' | 'infrastructure' | 'deployment';

export default function Environment() {
  const [activeTab, setActiveTab] = useState<TabType>('system');

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Environment</h1>
        <p className="page-description">System and infrastructure monitoring</p>
      </div>

      <div className="tabs-container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'system' ? 'active' : ''}`}
            onClick={() => setActiveTab('system')}
          >
            System
          </button>
          <button
            className={`tab ${activeTab === 'infrastructure' ? 'active' : ''}`}
            onClick={() => setActiveTab('infrastructure')}
          >
            Infrastructure
          </button>
          <button
            className={`tab ${activeTab === 'deployment' ? 'active' : ''}`}
            onClick={() => setActiveTab('deployment')}
          >
            Deployment
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'system' && <SystemMonitor />}
          {activeTab === 'infrastructure' && <InfrastructureMonitor />}
          {activeTab === 'deployment' && <DeploymentStatus />}
        </div>
      </div>
    </div>
  );
}
