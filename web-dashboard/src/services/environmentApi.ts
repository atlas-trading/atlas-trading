// Environment API services
import apiClient from './api';
import type { SystemMetrics, InfrastructureMetrics, ArgoDeploymentStatus } from '../types/environment';

export const environmentAPI = {
  // Get Mac Mini system metrics
  getSystemMetrics: async (): Promise<SystemMetrics> => {
    const response = await apiClient.get<SystemMetrics>('/system/metrics');
    return response.data;
  },

  // Get Kubernetes infrastructure metrics
  getInfraMetrics: async (): Promise<InfrastructureMetrics> => {
    const response = await apiClient.get<InfrastructureMetrics>('/infra/metrics');
    return response.data;
  },

  // Get ArgoCD deployment status
  getDeploymentStatus: async (): Promise<ArgoDeploymentStatus> => {
    const response = await apiClient.get<ArgoDeploymentStatus>('/deployment/status');
    return response.data;
  },
};
