import { useState, useEffect } from 'react';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';

export default function Header() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h2 className="header-title">Trading Dashboard</h2>
        </div>
        <div className="header-right">
          <button
            onClick={() => setIsDark(!isDark)}
            className="theme-toggle"
            aria-label="Toggle theme"
            style={{
              padding: '8px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
            }}
          >
            {isDark ? (
              <SunIcon style={{ width: '20px', height: '20px', color: 'var(--color-binance)' }} />
            ) : (
              <MoonIcon style={{ width: '20px', height: '20px', color: 'var(--text-primary)' }} />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
