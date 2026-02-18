import { useState, useCallback } from 'react';

const MAX_ENTRIES = 100;

export function useMetricsTSDB<T extends { timestamp: string }>(key: string) {
  const [history, setHistory] = useState<T[]>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const addEntry = useCallback((entry: T) => {
    setHistory(prev => {
      const updated = [...prev, entry];
      const trimmed = updated.length > MAX_ENTRIES
        ? updated.slice(updated.length - MAX_ENTRIES)
        : updated;
      try {
        localStorage.setItem(key, JSON.stringify(trimmed));
      } catch {
        // localStorage 용량 초과 시 무시
      }
      return trimmed;
    });
  }, [key]);

  const clearHistory = useCallback(() => {
    localStorage.removeItem(key);
    setHistory([]);
  }, [key]);

  return { history, addEntry, clearHistory };
}
