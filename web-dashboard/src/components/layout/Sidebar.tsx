import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  ChartBarIcon,
  BeakerIcon,
  CogIcon,
  ChartPieIcon,
  BanknotesIcon,
  CubeIcon,
  ClipboardDocumentListIcon
} from '@heroicons/react/24/outline';
import { useNetwork } from '../../contexts/NetworkContext';
import SettingsModal from '../common/SettingsModal';

interface MenuItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface MenuSection {
  title: string;
  items: MenuItem[];
}

const menuSections: MenuSection[] = [
  {
    title: 'Dashboard',
    items: [
      { label: 'Overview', path: '/', icon: HomeIcon },
    ]
  },
  {
    title: 'Trading',
    items: [
      { label: 'Balance & Portfolio', path: '/trading/balance', icon: BanknotesIcon },
      { label: 'Live Positions', path: '/trading/positions', icon: CubeIcon },
      { label: 'Order History', path: '/trading/orders', icon: ClipboardDocumentListIcon },
    ]
  },
  {
    title: 'Backtesting',
    items: [
      { label: 'Backtest List', path: '/backtests', icon: BeakerIcon },
      { label: 'Run New Backtest', path: '/backtests/run', icon: ChartBarIcon },
      { label: 'Compare', path: '/compare', icon: ChartPieIcon },
    ]
  },
  {
    title: 'Strategies',
    items: [
      { label: 'Strategy List', path: '/strategies', icon: CogIcon },
      { label: 'Edit Parameters', path: '/strategies/edit', icon: CogIcon },
    ]
  },
  {
    title: 'Analysis',
    items: [
      { label: 'Live Performance', path: '/analysis/live', icon: ChartBarIcon },
      { label: 'Backtest Analysis', path: '/analysis/backtest', icon: BeakerIcon },
      { label: 'Market Analysis', path: '/analysis/market', icon: ChartPieIcon },
      { label: 'Risk Monitoring', path: '/analysis/risk', icon: ChartBarIcon },
    ]
  },
];

export default function Sidebar() {
  const location = useLocation();
  const { network } = useNetwork();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-container">
          <img src="/logo.png" alt="Atlas Trading" className="sidebar-logo-img" />
          <h1 className="sidebar-logo">Atlas Trading</h1>
        </div>
        <div className={`network-badge ${network}`}>
          {network === 'testnet' ? 'Testnet' : 'Mainnet'}
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuSections.map((section, idx) => (
          <div key={idx} className="sidebar-section">
            <h3 className="sidebar-section-title">{section.title}</h3>
            <ul className="sidebar-menu">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);

                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className={`sidebar-menu-item ${active ? 'active' : ''}`}
                    >
                      <Icon className="sidebar-menu-icon" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Settings at bottom */}
      <div className="sidebar-settings">
        <ul className="sidebar-menu">
          <li>
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="sidebar-menu-item"
            >
              <CogIcon className="sidebar-menu-icon" />
              <span>Settings</span>
            </button>
          </li>
        </ul>
      </div>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <SettingsModal onClose={() => setIsSettingsOpen(false)} />
      )}
    </aside>
  );
}
