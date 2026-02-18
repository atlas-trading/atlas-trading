import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { NetworkProvider } from './contexts/NetworkContext';
import MainLayout from './components/layout/MainLayout';
import BacktestList from './pages/BacktestList';
import BacktestDetail from './pages/BacktestDetail';
import Dashboard from './pages/Dashboard';
import StrategyList from './pages/StrategyList';
import PaperTrading from './pages/PaperTrading';
import SystemPage from './pages/SystemPage';
import InfrastructurePage from './pages/InfrastructurePage';
import DeploymentPage from './pages/DeploymentPage';
import ComingSoon from './pages/ComingSoon';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <NetworkProvider>
          <MainLayout>
            <Routes>
              {/* Dashboard */}
              <Route path="/" element={<Dashboard />} />

              {/* Trading (Mainnet) */}
              <Route path="/trading/balance" element={<ComingSoon page="Balance & Portfolio" />} />

              {/* Backtest (Testnet) */}
              <Route path="/trading/paper" element={<PaperTrading />} />
              <Route path="/backtests" element={<BacktestList />} />
              <Route path="/backtest/:id" element={<BacktestDetail />} />

              {/* Strategies */}
              <Route path="/strategies" element={<StrategyList />} />

              {/* Environment - separate pages per tab */}
              <Route path="/environment" element={<Navigate to="/environment/system" replace />} />
              <Route path="/environment/system" element={<SystemPage />} />
              <Route path="/environment/infrastructure" element={<InfrastructurePage />} />
              <Route path="/environment/deployment" element={<DeploymentPage />} />

              {/* Analysis */}
              <Route path="/trading/orders" element={<ComingSoon page="Order History" />} />
            </Routes>
        </MainLayout>
        </NetworkProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
