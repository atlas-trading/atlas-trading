/**
 * Paper Trading API Client
 * Based on backend API: app/api/v1/paper_trading.py
 */
import apiClient from './api';
import type {
  PaperTradingSession,
  PaperTradingSessionCreate,
  PaperTradingTrade,
  PaperTradingSnapshot,
  PaperTradingStats,
  SessionStatus,
  KlineData,
} from '../types/paper_trading';

export const paperTradingAPI = {
  /**
   * Get list of paper trading sessions
   * @param status Filter by session status (optional)
   * @param skip Number of records to skip (pagination)
   * @param limit Maximum number of records to return
   */
  listSessions: async (
    status?: SessionStatus,
    skip: number = 0,
    limit: number = 100
  ): Promise<PaperTradingSession[]> => {
    const params: Record<string, any> = { skip, limit };
    if (status) {
      params.status = status;
    }

    const response = await apiClient.get<PaperTradingSession[]>('/paper-trading/sessions', {
      params,
    });
    return response.data;
  },

  /**
   * Get session details
   * @param sessionId Session ID
   */
  getSession: async (sessionId: number): Promise<PaperTradingSession> => {
    const response = await apiClient.get<PaperTradingSession>(
      `/paper-trading/sessions/${sessionId}`
    );
    return response.data;
  },

  /**
   * Create a new paper trading session
   * @param data Session creation data
   */
  createSession: async (data: PaperTradingSessionCreate): Promise<PaperTradingSession> => {
    const response = await apiClient.post<PaperTradingSession>(
      '/paper-trading/sessions',
      data
    );
    return response.data;
  },

  /**
   * Delete a paper trading session
   * @param sessionId Session ID
   */
  deleteSession: async (sessionId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(
      `/paper-trading/sessions/${sessionId}`
    );
    return response.data;
  },

  /**
   * Get trades for a session
   * @param sessionId Session ID
   * @param skip Number of records to skip (pagination)
   * @param limit Maximum number of records to return
   */
  getSessionTrades: async (
    sessionId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<PaperTradingTrade[]> => {
    const response = await apiClient.get<PaperTradingTrade[]>(
      `/paper-trading/sessions/${sessionId}/trades`,
      {
        params: { skip, limit },
      }
    );
    return response.data;
  },

  /**
   * Get snapshots for a session (for equity curve)
   * @param sessionId Session ID
   * @param startTime Filter start time (ISO 8601 string, optional)
   * @param endTime Filter end time (ISO 8601 string, optional)
   * @param limit Maximum number of records to return
   */
  getSessionSnapshots: async (
    sessionId: number,
    startTime?: string,
    endTime?: string,
    limit: number = 1000
  ): Promise<PaperTradingSnapshot[]> => {
    const params: Record<string, any> = { limit };
    if (startTime) {
      params.start_time = startTime;
    }
    if (endTime) {
      params.end_time = endTime;
    }

    const response = await apiClient.get<PaperTradingSnapshot[]>(
      `/paper-trading/sessions/${sessionId}/snapshots`,
      {
        params,
      }
    );
    return response.data;
  },

  /**
   * Get statistics for a session
   * @param sessionId Session ID
   */
  getSessionStats: async (sessionId: number): Promise<PaperTradingStats> => {
    const response = await apiClient.get<PaperTradingStats>(
      `/paper-trading/sessions/${sessionId}/stats`
    );
    return response.data;
  },

  /**
   * Control session (start, pause, stop)
   * @param sessionId Session ID
   * @param action Control action: 'start' | 'pause' | 'stop'
   */
  controlSession: async (
    sessionId: number,
    action: 'start' | 'pause' | 'stop'
  ): Promise<{ message: string; status: SessionStatus }> => {
    const response = await apiClient.post<{ message: string; status: SessionStatus }>(
      `/paper-trading/sessions/${sessionId}/control/${action}`
    );
    return response.data;
  },

  /**
   * Get K-line data for a session (for chart display)
   * @param sessionId Session ID
   * @param interval Kline interval (e.g., '1m', '5m', '15m', '1h')
   * @param limit Maximum number of klines to return (default: 500)
   */
  getSessionKlines: async (
    sessionId: number,
    interval: string = '1m',
    limit: number = 500
  ): Promise<KlineData[]> => {
    const response = await apiClient.get<KlineData[]>(
      `/paper-trading/sessions/${sessionId}/klines`,
      {
        params: { interval, limit },
      }
    );
    return response.data;
  },
};

export default paperTradingAPI;
