export interface Trade {
  id: string;
  strategy: string;
  status: string;
  expected_profit: string | null;
  actual_profit: string | null;
  created_at: string;
  completed_at: string | null;
}

export async function fetchTrades(limit = 50): Promise<Trade[]> {
  const res = await fetch(`/trades?limit=${limit}`);
  return res.json();
}
