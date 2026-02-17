import { useState } from 'react';
import SystemMonitor from '../components/environment/SystemMonitor';
import InfrastructureMonitor from '../components/environment/InfrastructureMonitor';

type TabType = 'system' | 'infrastructure';

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
        </div>

        <div className="tab-content">
          {activeTab === 'system' && <SystemMonitor />}
          {activeTab === 'infrastructure' && <InfrastructureMonitor />}
        </div>
      </div>
    </div>
  );
}
