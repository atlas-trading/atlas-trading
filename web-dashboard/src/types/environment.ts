// Environment metrics types

export interface SystemMetrics {
  cpu_temp: number;
  gpu_temp: number;
  cpu_power: number;
  gpu_power: number;
  memory_used: number;
  memory_total: number;
  disk_used: number;
  disk_total: number;
  timestamp: string;
}

export interface InfrastructureMetrics {
  nodes_total: number;
  nodes_ready: number;
  pods_total: number;
  pods_running: number;
  cpu_usage: number;
  cpu_total: number;
  memory_usage: number;
  memory_total: number;
  deployments: DeploymentStatus[];
  timestamp: string;
}

export interface DeploymentStatus {
  name: string;
  namespace: string;
  replicas: number;
  ready_replicas: number;
  available: boolean;
}
