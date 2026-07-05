import { useEffect, useState } from "react";
import {
  BacktestRun,
  BacktestTrade,
  fetchBacktestRuns,
  fetchBacktestTrades,
} from "../api/backtests";

const STATUS_COLOR: Record<string, string> = {
  COMPLETE: "text-green-600 font-semibold",
  UNWIND_COMPLETE: "text-yellow-600 font-semibold",
  TIMEOUT: "text-gray-400",
  FAILED: "text-red-500",
};

function pnlColor(value: string): string {
  return parseFloat(value) >= 0 ? "text-green-600" : "text-red-600";
}

function SummaryCard({ label, value, className = "" }: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold ${className}`}>{value}</p>
    </div>
  );
}

export function BacktestPanel() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selected, setSelected] = useState<BacktestRun | null>(null);
  const [trades, setTrades] = useState<BacktestTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBacktestRuns()
      .then((rs) => {
        setRuns(rs);
        if (rs.length > 0) setSelected(rs[0]);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchBacktestTrades(selected.id)
      .then(setTrades)
      .catch((err) => setError(String(err)));
  }, [selected]);

  if (loading) return <p className="text-gray-400 text-sm">불러오는 중...</p>;
  if (error) return <p className="text-red-500 text-sm">오류: {error}</p>;
  if (runs.length === 0)
    return <p className="text-gray-400 text-sm">백테스트 실행 이력 없음</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-1">
        <ul className="divide-y">
          {runs.map((run) => (
            <li key={run.id}>
              <button
                onClick={() => setSelected(run)}
                className={`w-full text-left px-3 py-2 rounded hover:bg-gray-50 ${
                  selected?.id === run.id ? "bg-blue-50" : ""
                }`}
              >
                <span className="font-mono text-xs text-gray-500">
                  #{run.id}
                </span>{" "}
                <span className="text-sm">
                  {run.start_date.slice(0, 10)} ~ {run.end_date.slice(0, 10)}
                </span>
                <span className={`ml-2 text-sm ${pnlColor(run.total_pnl)}`}>
                  {parseFloat(run.total_pnl).toFixed(4)} USDT
                </span>
                <span className="ml-2 text-xs text-gray-400">
                  {run.trade_count}건
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="lg:col-span-2">
        {selected && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <SummaryCard
                label="총 PnL"
                value={`${parseFloat(selected.total_pnl).toFixed(4)} USDT`}
                className={pnlColor(selected.total_pnl)}
              />
              <SummaryCard
                label="승률"
                value={`${(selected.win_rate * 100).toFixed(1)}%`}
              />
              <SummaryCard label="거래 수" value={String(selected.trade_count)} />
              <SummaryCard
                label="초기 → 최종"
                value={`${parseFloat(selected.initial_balance).toFixed(0)} → ${parseFloat(selected.final_balance).toFixed(2)}`}
              />
            </div>

            {trades.length === 0 ? (
              <p className="text-gray-400 text-sm">거래 없음</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-100 text-gray-600 uppercase text-xs">
                    <tr>
                      <th className="px-4 py-2">시간</th>
                      <th className="px-4 py-2">경로</th>
                      <th className="px-4 py-2">상태</th>
                      <th className="px-4 py-2">예상 수익</th>
                      <th className="px-4 py-2">실제 수익</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs">
                          {new Date(t.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 text-xs">
                          {t.leg1_pair} → {t.leg2_pair} → {t.leg3_pair}
                        </td>
                        <td className={`px-4 py-2 ${STATUS_COLOR[t.status] ?? ""}`}>
                          {t.status}
                        </td>
                        <td className="px-4 py-2">{t.expected_profit}</td>
                        <td
                          className={`px-4 py-2 ${
                            t.actual_profit !== null
                              ? pnlColor(t.actual_profit)
                              : ""
                          }`}
                        >
                          {t.actual_profit ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
