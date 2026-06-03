import { useEffect, useState } from "react";

export interface Alert {
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
      const data = JSON.parse(e.data) as Omit<Alert, "ts">;
      setAlerts((prev) =>
        [{ ...data, ts: new Date().toISOString() }, ...prev].slice(0, 50)
      );
    };
    return () => ws.close();
  }, []);

  return alerts;
}
