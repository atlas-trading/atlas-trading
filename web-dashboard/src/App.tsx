import { AlertFeed } from "./components/AlertFeed";
import { TradeTable } from "./components/TradeTable";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        Atlas Trading — 어드민
      </h1>

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
    </div>
  );
}
