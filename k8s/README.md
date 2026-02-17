# Kubernetes Manifests

This directory contains Kubernetes manifests for deploying Atlas Trading platform.

## Directory Structure

```
k8s/
├── argocd/
│   └── application.yaml    # ArgoCD Application definition
└── README.md
```

## Deployment with ArgoCD

ArgoCD monitors this directory and automatically deploys changes pushed to the `main` branch.

### Setup

1. Ensure ArgoCD is installed (see `/docs/ARGOCD.md`)
2. Update GitHub username in `argocd/application.yaml`
3. Apply the ArgoCD application:
```bash
kubectl apply -f k8s/argocd/application.yaml
```

### Adding New Services

Create manifests in this directory following this structure:

```
k8s/
├── <service-name>/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml (optional)
```

Example:
```
k8s/
├── api-server/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── web-dashboard/
│   ├── deployment.yaml
│   └── service.yaml
```

## Manual Deployment (without ArgoCD)

```bash
kubectl apply -f k8s/<service-name>/
```

## Namespaces

- `default`: Application services
- `argocd`: ArgoCD GitOps controller

## Next Steps

1. Create deployment manifests for:
   - PostgreSQL
   - Redis
   - API Server
   - Web Dashboard
   - Trading Engine

2. Configure ConfigMaps and Secrets
3. Set up Ingress or LoadBalancer services
