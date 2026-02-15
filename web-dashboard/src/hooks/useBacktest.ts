// Custom hook for fetching backtest data
import { useState, useEffect } from 'react';
import { backtestAPI } from '../services/api';
import type { BacktestRunDetail, BacktestRunFull } from '../types/backtest';

export function useBacktest(id: number | string) {
  const [data, setData] = useState<BacktestRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBacktest();
  }, [id]);

  const loadBacktest = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await backtestAPI.getBacktest(Number(id));
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '백테스트 데이터를 불러오는데 실패했습니다.');
      console.error('Failed to load backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, refetch: loadBacktest };
}

export function useBacktestFull(id: number | string) {
  const [data, setData] = useState<BacktestRunFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBacktest();
  }, [id]);

  const loadBacktest = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await backtestAPI.getBacktestFull(Number(id));
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '백테스트 데이터를 불러오는데 실패했습니다.');
      console.error('Failed to load backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, refetch: loadBacktest };
}
