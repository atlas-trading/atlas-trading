// API client using Axios
import axios from 'axios';
import type {
  BacktestRunSummary,
  BacktestRunDetail,
  BacktestRunFull,
  Trade,
  EquityPoint,
  AdvancedMetrics,
  TradeAnalysis,
  MonteCarloResult,
  CostStressResult,
} from '../types/backtest';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// API response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const backtestAPI = {
  // Get list of backtests
  listBacktests: async (params?: {
    skip?: number;
    limit?: number;
    strategy_name?: string;
    symbol?: string;
  }): Promise<BacktestRunSummary[]> => {
    const response = await apiClient.get<BacktestRunSummary[]>('/backtests/', {
      params,
      maxRedirects: 5  // Follow redirects
    });
    return response.data;
  },

  // Get backtest detail (without trades and equity)
  getBacktest: async (id: number): Promise<BacktestRunDetail> => {
    const response = await apiClient.get<BacktestRunDetail>(`/backtests/${id}`);
    return response.data;
  },

  // Get full backtest data (with trades and equity)
  getBacktestFull: async (id: number): Promise<BacktestRunFull> => {
    const response = await apiClient.get<BacktestRunFull>(`/backtests/${id}/full`);
    return response.data;
  },

  // Get trades only
  getTrades: async (id: number): Promise<Trade[]> => {
    const response = await apiClient.get<Trade[]>(`/backtests/${id}/trades`);
    return response.data;
  },

  // Get equity curve only
  getEquityCurve: async (id: number): Promise<EquityPoint[]> => {
    const response = await apiClient.get<EquityPoint[]>(`/backtests/${id}/equity`);
    return response.data;
  },

  // Get advanced metrics
  getAdvancedMetrics: async (id: number): Promise<AdvancedMetrics> => {
    const response = await apiClient.get<AdvancedMetrics>(`/backtests/${id}/metrics/advanced`);
    return response.data;
  },

  // Get trade analysis
  getTradeAnalysis: async (id: number): Promise<TradeAnalysis> => {
    const response = await apiClient.get<TradeAnalysis>(`/backtests/${id}/analysis/trades`);
    return response.data;
  },

  // Run Monte Carlo simulation
  runMonteCarlo: async (id: number, nSimulations: number = 1000): Promise<MonteCarloResult> => {
    const response = await apiClient.post<MonteCarloResult>(
      `/backtests/${id}/monte-carlo?n_simulations=${nSimulations}`
    );
    return response.data;
  },

  // Run Cost Stress Test
  runCostStressTest: async (id: number): Promise<CostStressResult> => {
    const response = await apiClient.post<CostStressResult>(
      `/backtests/${id}/cost-stress`
    );
    return response.data;
  },
};

// Strategy API
export interface Strategy {
  name: string;
  description?: string;
}

export const strategyAPI = {
  // Get available strategies
  getAvailableStrategies: async (): Promise<Strategy[]> => {
    const response = await apiClient.get<Strategy[]>('/strategies/available');
    return response.data;
  },
};

// Market API
export interface MarketSymbol {
  symbol: string;
  description?: string;
}

export interface Timeframe {
  value: string;
  label: string;
}

export const marketAPI = {
  // Get available symbols
  getSymbols: async (): Promise<MarketSymbol[]> => {
    const response = await apiClient.get<MarketSymbol[]>('/market/symbols');
    return response.data;
  },

  // Get available timeframes
  getTimeframes: async (): Promise<Timeframe[]> => {
    const response = await apiClient.get<Timeframe[]>('/market/timeframes');
    return response.data;
  },
};

export default apiClient;
