import InfrastructureMonitor from '../components/environment/InfrastructureMonitor';

export default function InfrastructurePage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Infrastructure</h1>
        <p className="page-description">Kubernetes cluster nodes, pods, and resource usage</p>
      </div>
      <InfrastructureMonitor />
    </div>
  );
}
