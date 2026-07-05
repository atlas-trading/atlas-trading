import { useState } from "react";
import { AlertFeed } from "./components/AlertFeed";
import { BacktestPanel } from "./components/BacktestPanel";
import { TradeTable } from "./components/TradeTable";

const TABS = [
  { key: "live", label: "실시간" },
  { key: "backtest", label: "백테스트" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function App() {
  const [tab, setTab] = useState<TabKey>("live");

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        Atlas Trading — 어드민
      </h1>

      <nav className="flex gap-2 mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              tab === t.key
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "live" ? (
        <div className="grid grid-cols-1 gap-6">
          <section className="bg-white rounded-xl shadow p-4">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              실시간 알림
            </h2>
            <AlertFeed />
          </section>

          <section className="bg-white rounded-xl shadow p-4">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              거래 내역
            </h2>
            <TradeTable />
          </section>
        </div>
      ) : (
        <section className="bg-white rounded-xl shadow p-4">
          <h2 className="text-lg font-semibold text-gray-700 mb-3">
            백테스트 결과
          </h2>
          <BacktestPanel />
        </section>
      )}
    </div>
  );
}
