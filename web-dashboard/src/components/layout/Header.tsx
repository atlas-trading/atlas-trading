import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../../contexts/ThemeContext';

export default function Header() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h2 className="header-title">Trading Dashboard</h2>
        </div>

        <div className="header-right">
          <button
            onClick={toggleTheme}
            className="theme-toggle"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <SunIcon className="w-5 h-5" />
            ) : (
              <MoonIcon className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
