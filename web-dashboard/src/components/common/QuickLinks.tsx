export default function QuickLinks() {
  const links = [
    {
      name: 'Grafana',
      description: 'Metrics & Monitoring',
      url: 'http://100.110.86.86:31177',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      color: '#F0B90B',
    },
    {
      name: 'Prometheus',
      description: 'Time Series Database',
      url: 'http://100.110.86.86:9090',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
        </svg>
      ),
      color: '#E6522C',
    },
    {
      name: 'ArgoCD',
      description: 'GitOps Deployment',
      url: 'http://172.30.1.61:32431',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
      color: '#0ECB81',
    },
    {
      name: 'Kubernetes',
      description: 'Cluster Dashboard',
      url: 'http://100.110.86.86:31177/d/k8s-cluster',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
      ),
      color: '#326CE5',
    },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Quick Links</h2>
        <p className="text-muted text-sm">Infrastructure monitoring and deployment tools</p>
      </div>
      <div className="card-body">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {links.map((link) => (
            <a
              key={link.name}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="quick-link-card"
              style={{ borderLeftColor: link.color }}
            >
              <div className="quick-link-icon" style={{ color: link.color }}>
                {link.icon}
              </div>
              <div className="quick-link-content">
                <div className="quick-link-name">{link.name}</div>
                <div className="quick-link-description">{link.description}</div>
              </div>
              <div className="quick-link-arrow">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </a>
          ))}
        </div>

        <div className="mt-6 p-4 bg-tertiary rounded-lg border border-primary">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-warning mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm">
              <p className="text-secondary font-medium mb-1">Tailscale Network Access</p>
              <p className="text-tertiary">These services are only accessible within the Tailscale VPN network for security.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
