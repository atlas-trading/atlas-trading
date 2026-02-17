import QuickLinks from '../components/common/QuickLinks';

export default function Dashboard() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Dashboard Overview</h1>
        <p className="page-description">Welcome to Atlas Trading</p>
      </div>

      <div className="mb-8">
        <QuickLinks />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="stat-card">
          <div className="stat-card-label">Total Backtests</div>
          <div className="stat-card-value">0</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Active Strategies</div>
          <div className="stat-card-value">0</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Live Balance</div>
          <div className="stat-card-value">$0.00</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Total PnL</div>
          <div className="stat-card-value text-green-400">+0.00%</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Quick Actions</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a href="/backtests/run" className="action-card">
              <h3 className="text-lg font-semibold mb-2">Run Backtest</h3>
              <p className="text-sm opacity-70">Test your strategies on historical data</p>
            </a>
            <a href="/backtests" className="action-card">
              <h3 className="text-lg font-semibold mb-2">View Results</h3>
              <p className="text-sm opacity-70">Analyze past backtest performance</p>
            </a>
            <a href="/strategies" className="action-card">
              <h3 className="text-lg font-semibold mb-2">Manage Strategies</h3>
              <p className="text-sm opacity-70">Configure and optimize strategies</p>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
