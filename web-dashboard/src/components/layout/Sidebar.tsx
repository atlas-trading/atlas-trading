import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  BeakerIcon,
  BanknotesIcon,
  ClipboardDocumentListIcon,
  PlayIcon,
  ServerIcon,
  CpuChipIcon,
  RocketLaunchIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { useNetwork } from '../../contexts/NetworkContext';

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
    title: 'DASHBOARD',
    items: [
      { label: 'Overview', path: '/', icon: HomeIcon },
    ]
  },
  {
    title: 'TRADING (Mainnet)',
    items: [
      { label: 'Balance', path: '/trading/balance', icon: BanknotesIcon },
    ]
  },
  {
    title: 'BACKTEST (Testnet)',
    items: [
      { label: 'Paper Trading', path: '/trading/paper', icon: PlayIcon },
      { label: 'Backtest List', path: '/backtests', icon: BeakerIcon },
    ]
  },
  {
    title: 'ANALYSIS',
    items: [
      { label: 'Order History', path: '/trading/orders', icon: ClipboardDocumentListIcon },
    ]
  },
  {
    title: 'ENVIRONMENT',
    items: [
      { label: 'System', path: '/environment/system', icon: CpuChipIcon },
      { label: 'Infrastructure', path: '/environment/infrastructure', icon: ServerIcon },
      { label: 'Deployment', path: '/environment/deployment', icon: RocketLaunchIcon },
    ]
  },
  {
    title: 'ADMIN',
    items: [
      { label: 'API Keys', path: '/admin/secrets', icon: KeyIcon },
    ]
  },
];

export default function Sidebar() {
  const location = useLocation();
  const { network } = useNetwork();

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
    </aside>
  );
}
