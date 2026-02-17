// Environment API services
import apiClient from './api';
import type { SystemMetrics, InfrastructureMetrics } from '../types/environment';

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
};
