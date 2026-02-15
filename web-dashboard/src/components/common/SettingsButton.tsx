import { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { useNetwork, type Network } from '../../contexts/NetworkContext';
import './SettingsButton.css';

export default function SettingsButton() {
  const [isOpen, setIsOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { network, setNetwork } = useNetwork();

  return (
    <>
      {/* Settings Button */}
      <button
        className="settings-button"
        onClick={() => setIsOpen(true)}
        title="Settings"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v6m0 6v6m-6-6h6m6 0h6m-2.5-6.5l-4.2 4.2m0 4.6l4.2 4.2m-12.6 0l4.2-4.2m0-4.6l-4.2-4.2" />
        </svg>
      </button>

      {/* Settings Modal */}
      {isOpen && (
        <div className="settings-modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h2>Settings</h2>
              <button className="close-button" onClick={() => setIsOpen(false)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="settings-content">
              {/* Theme Toggle */}
              <div className="setting-item">
                <div className="setting-info">
                  <label>Theme</label>
                  <span className="setting-description">
                    Switch between dark and light mode
                  </span>
                </div>
                <div className="setting-control">
                  <button
                    className={`toggle-button ${theme === 'dark' ? 'active' : ''}`}
                    onClick={toggleTheme}
                  >
                    <span className={theme === 'dark' ? 'active' : ''}>Dark</span>
                    <span className={theme === 'light' ? 'active' : ''}>Light</span>
                    <div className="toggle-slider" />
                  </button>
                </div>
              </div>

              {/* Network Toggle */}
              <div className="setting-item">
                <div className="setting-info">
                  <label>Network</label>
                  <span className="setting-description">
                    Switch between testnet and mainnet
                  </span>
                </div>
                <div className="setting-control">
                  <button
                    className={`toggle-button ${network === 'testnet' ? 'active' : ''}`}
                    onClick={() => setNetwork(network === 'testnet' ? 'mainnet' : 'testnet')}
                  >
                    <span className={network === 'testnet' ? 'active' : ''}>Testnet</span>
                    <span className={network === 'mainnet' ? 'active' : ''}>Mainnet</span>
                    <div className="toggle-slider" />
                  </button>
                </div>
              </div>

              {/* Network Warning */}
              {network === 'mainnet' && (
                <div className="warning-box">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  <span>You are viewing <strong>MAINNET</strong> data. Real money is involved.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
