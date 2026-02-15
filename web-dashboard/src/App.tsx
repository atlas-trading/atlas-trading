import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import MainLayout from './components/layout/MainLayout';
import BacktestList from './pages/BacktestList';
import BacktestDetail from './pages/BacktestDetail';
import BacktestCompare from './pages/BacktestCompare';
import BacktestRun from './pages/BacktestRun';
import Dashboard from './pages/Dashboard';
import StrategyList from './pages/StrategyList';
import ComingSoon from './pages/ComingSoon';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />

            {/* Trading */}
            <Route path="/trading/balance" element={<ComingSoon page="Balance & Portfolio" />} />
            <Route path="/trading/positions" element={<ComingSoon page="Live Positions" />} />
            <Route path="/trading/orders" element={<ComingSoon page="Order History" />} />

            {/* Backtesting */}
            <Route path="/backtests" element={<BacktestList />} />
            <Route path="/backtests/run" element={<BacktestRun />} />
            <Route path="/backtest/:id" element={<BacktestDetail />} />
            <Route path="/compare" element={<BacktestCompare />} />

            {/* Strategies */}
            <Route path="/strategies" element={<StrategyList />} />
            <Route path="/strategies/edit/:strategyName" element={<ComingSoon page="Edit Parameters" />} />
            <Route path="/strategies/add/:strategyName" element={<ComingSoon page="Add Strategy" />} />

            {/* Analysis */}
            <Route path="/analysis/live" element={<ComingSoon page="Live Performance" />} />
            <Route path="/analysis/backtest" element={<Navigate to="/backtests" replace />} />
            <Route path="/analysis/market" element={<ComingSoon page="Market Analysis" />} />
            <Route path="/analysis/risk" element={<ComingSoon page="Risk Monitoring" />} />
          </Routes>
        </MainLayout>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
