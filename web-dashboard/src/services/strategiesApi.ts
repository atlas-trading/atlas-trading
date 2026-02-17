/**
 * Strategies API Client
 * Based on backend API: app/api/v1/strategies.py
 */
import apiClient from './api';

export interface ParameterSchema {
  name: string;
  type: 'int' | 'float' | 'bool' | 'string' | 'select';
  default: any;
  min?: number;
  max?: number;
  step?: number;
  options?: any[];
  description: string;
  required: boolean;
}

export interface StrategyInfo {
  strategy_name: string;
  display_name: string;
  description: string;
  parameter_schema: ParameterSchema[];
}

export const strategiesAPI = {
  /**
   * Get list of available strategies
   */
  listStrategies: async (): Promise<StrategyInfo[]> => {
    const response = await apiClient.get<StrategyInfo[]>('/strategies/available');
    return response.data;
  },

  /**
   * Get list of supported symbols
   */
  listSymbols: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/strategies/symbols');
    return response.data;
  },

  /**
   * Get detailed info for a specific strategy
   */
  getStrategyInfo: async (strategyName: string): Promise<StrategyInfo> => {
    const response = await apiClient.get<StrategyInfo>(`/strategies/${strategyName}`);
    return response.data;
  },
};

export default strategiesAPI;
