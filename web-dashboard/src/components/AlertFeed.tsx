import { useAlerts } from "../api/alerts";

const BG: Record<string, string> = {
  COMPLETE: "bg-green-50 border-green-200",
  UNWIND_COMPLETE: "bg-yellow-50 border-yellow-200",
  TIMEOUT: "bg-gray-50 border-gray-200",
};

export function AlertFeed() {
  const alerts = useAlerts();

  return (
    <div className="h-48 overflow-y-auto space-y-1">
      {alerts.length === 0 && (
        <p className="text-gray-400 text-sm">대기 중...</p>
      )}
      {alerts.map((a) => (
        <div
          key={a.id}
          className={`text-sm px-3 py-1.5 rounded border ${BG[a.type] ?? "bg-gray-50 border-gray-200"}`}
        >
          <span className="font-mono text-xs text-gray-400">
            {new Date(a.ts).toLocaleTimeString()}
          </span>{" "}
          <strong>{a.type}</strong> | {a.arb_id.slice(0, 8)}… | PnL:{" "}
          <span
            className={
              parseFloat(a.pnl ?? "0") >= 0 ? "text-green-600" : "text-red-600"
            }
          >
            {a.pnl}
          </span>
        </div>
      ))}
    </div>
  );
}
