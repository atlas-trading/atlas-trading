import SystemMonitor from '../components/environment/SystemMonitor';

export default function SystemPage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">System</h1>
        <p className="page-description">Mac Mini hardware metrics (CPU, GPU, Memory, Disk)</p>
      </div>
      <SystemMonitor />
    </div>
  );
}
