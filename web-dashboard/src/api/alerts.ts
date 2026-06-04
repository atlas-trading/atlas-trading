import { useEffect, useState } from "react";

export interface Alert {
  id: string;
  type: string;
  arb_id: string;
  pnl: string;
  ts: string;
}

export function useAlerts(): Alert[] {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/alerts`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as Omit<Alert, "ts" | "id">;
      const ts = new Date().toISOString();
      // Stable id keyed on arb_id+ts so React's reconciler doesn't reuse rows
      // when the same arb is alerted twice.
      const id = `${data.arb_id}:${ts}`;
      setAlerts((prev) => [{ ...data, id, ts }, ...prev].slice(0, 50));
    };
    return () => ws.close();
  }, []);

  return alerts;
}
