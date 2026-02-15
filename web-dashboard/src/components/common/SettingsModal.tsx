import { useTheme } from '../../contexts/ThemeContext';
import { useNetwork, type Network } from '../../contexts/NetworkContext';
import { useEffect, useRef } from 'react';
import './SettingsButton.css';

interface SettingsModalProps {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
  const { theme, toggleTheme } = useTheme();
  const { network, setNetwork } = useNetwork();
  const themeSliderRef = useRef<HTMLDivElement>(null);
  const networkSliderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const updateSlider = (sliderRef: React.RefObject<HTMLDivElement>, activeValue: string) => {
      if (!sliderRef.current) return;
      const button = sliderRef.current.parentElement;
      if (!button) return;

      const spans = button.querySelectorAll('span');
      let activeSpan: Element | null = null;

      spans.forEach(span => {
        if (span.classList.contains('active')) {
          activeSpan = span;
        }
      });

      if (activeSpan) {
        const spanRect = activeSpan.getBoundingClientRect();
        const buttonRect = button.getBoundingClientRect();
        const left = spanRect.left - buttonRect.left + 4; // Add 4px left margin
        const width = spanRect.width - 8; // Subtract 8px for left+right margin

        sliderRef.current.style.left = `${left}px`;
        sliderRef.current.style.width = `${width}px`;
      }
    };

    updateSlider(themeSliderRef, theme);
    updateSlider(networkSliderRef, network);
  }, [theme, network]);

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="close-button" onClick={onClose}>
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
                <div className="toggle-slider" ref={themeSliderRef} />
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
                <div className="toggle-slider" ref={networkSliderRef} />
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
  );
}
