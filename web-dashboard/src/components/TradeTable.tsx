import { useEffect, useRef, useState } from "react";
import { fetchTrades, Trade } from "../api/trades";

const STATUS_COLOR: Record<string, string> = {
  COMPLETE: "text-green-600 font-semibold",
  UNWIND_COMPLETE: "text-yellow-600 font-semibold",
  TIMEOUT: "text-gray-400",
  PENDING: "text-blue-500",
};

export function TradeTable() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const applyTrades = (next: Trade[]) => {
      // L-9: guard against late responses after unmount.
      if (mountedRef.current) setTrades(next);
    };
    const stopLoading = () => {
      if (mountedRef.current) setLoading(false);
    };

    fetchTrades()
      .then(applyTrades)
      .catch((err) => console.error("fetchTrades failed", err))
      .finally(stopLoading);

    const id = setInterval(() => {
      fetchTrades()
        .then(applyTrades)
        .catch((err) => console.error("fetchTrades failed", err));
    }, 5000);

    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, []);

  if (loading) return <p className="text-gray-400 text-sm">불러오는 중...</p>;
  if (trades.length === 0)
    return <p className="text-gray-400 text-sm">거래 내역 없음</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="bg-gray-100 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2">시간</th>
            <th className="px-4 py-2">전략</th>
            <th className="px-4 py-2">상태</th>
            <th className="px-4 py-2">예상 수익</th>
            <th className="px-4 py-2">실제 수익</th>
            <th className="px-4 py-2">완료</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b hover:bg-gray-50">
              <td className="px-4 py-2 font-mono text-xs">
                {new Date(t.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-2">{t.strategy}</td>
              <td className={`px-4 py-2 ${STATUS_COLOR[t.status] ?? ""}`}>
                {t.status}
              </td>
              <td className="px-4 py-2">{t.expected_profit ?? "—"}</td>
              <td
                className={`px-4 py-2 ${
                  parseFloat(t.actual_profit ?? "0") >= 0
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {t.actual_profit ?? "—"}
              </td>
              <td className="px-4 py-2 text-xs text-gray-400">
                {t.completed_at
                  ? new Date(t.completed_at).toLocaleTimeString()
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
