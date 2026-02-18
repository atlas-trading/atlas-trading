import DeploymentStatus from '../components/environment/DeploymentStatus';

export default function DeploymentPage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Deployment</h1>
        <p className="page-description">ArgoCD application health and GitOps sync status</p>
      </div>
      <DeploymentStatus />
    </div>
  );
}
