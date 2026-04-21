import { memo, useCallback, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { SIDEBAR_WIDTH } from '@/utils/constants';

interface NavItem {
  path: string;
  icon: string;
  label: string;
  iconSize?: number;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', icon: '/assets/sidebar/icons/menu.svg', label: 'Dashboard', iconSize: 36 },
  { path: '/analysis', icon: '/assets/sidebar/icons/widget.svg', label: 'Analysis', iconSize: 36 },
  { path: '/trades', icon: '/assets/sidebar/icons/Trade.svg', label: 'Active Trades', iconSize: 36 },
  { path: '/journal', icon: '/assets/sidebar/icons/analytics.svg', label: 'Journal', iconSize: 36 },
  { path: '/settings', icon: '/assets/sidebar/icons/wallet.svg', label: 'Settings', iconSize: 36 },
];

function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ top: 0 });

  const isActive = useCallback(
    (path: string) => {
      if (path === '/') return location.pathname === '/';
      return location.pathname.startsWith(path);
    },
    [location.pathname],
  );

  const handleMouseEnter = useCallback((label: string, e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltipPos({ top: rect.top + rect.height / 2 });
    setHovered(label);
  }, []);

  return (
    <aside
      className="fixed left-0 top-0 h-screen flex flex-col z-sidebar overflow-hidden
                 border-r border-border"
      style={{
        width: SIDEBAR_WIDTH,
        background: 'linear-gradient(180deg, var(--surface-1) 0%, var(--surface-3) 100%)',
      }}
    >
      {/* Logo */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center justify-center w-full h-12 mb-2 cursor-pointer"
        aria-label="Home"
      >
        <img src="/assets/sidebar/icons/logo.svg" alt="eTradie" width={37} height={37} className="select-none" />
      </button>

      {/* Navigation */}
      <div className="flex-1 flex flex-col justify-between">
        <nav className="flex flex-col">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                onMouseEnter={(e) => handleMouseEnter(item.label, e)}
                onMouseLeave={() => setHovered(null)}
                className="relative flex items-center justify-center w-full h-12 mb-1
                           transition-all duration-200 cursor-pointer border-none bg-transparent"
                aria-label={item.label}
              >
                {active && (
                  <>
                    <span className="absolute left-0.5 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-brand rounded-full" />
                    <span
                      className="absolute inset-1.5 rounded-lg pointer-events-none"
                      style={{
                        background: 'radial-gradient(circle, rgba(232,81,2,0.12) 0%, transparent 70%)',
                      }}
                    />
                  </>
                )}
                <img
                  src={item.icon}
                  alt={item.label}
                  width={item.iconSize || 28}
                  height={item.iconSize || 28}
                  className="select-none transition-transform duration-200"
                />
              </button>
            );
          })}
        </nav>

        {/* Bottom actions */}
        <div className="relative flex flex-col items-center mb-8">
          <img
            src="/assets/sidebar/icons/Setting-support.svg"
            alt="Settings and Support"
            width={37}
            height={82}
            className="select-none"
          />
          <button
            onClick={() => navigate('/settings')}
            onMouseEnter={(e) => handleMouseEnter('Settings', e)}
            onMouseLeave={() => setHovered(null)}
            className="absolute top-0 left-0 w-full h-[41px] bg-transparent border-none cursor-pointer rounded-lg"
            aria-label="Settings"
          />
          <button
            onMouseEnter={(e) => handleMouseEnter('Support', e)}
            onMouseLeave={() => setHovered(null)}
            className="absolute bottom-0 left-0 w-full h-[41px] bg-transparent border-none cursor-pointer rounded-lg"
            aria-label="Support"
          />
        </div>
      </div>

      {/* Tooltip */}
      {hovered && (
        <div
          className="fixed z-[9999] px-3 py-1.5 rounded-md text-xs font-medium text-white
                     bg-surface-3 border border-border shadow-dropdown pointer-events-none"
          style={{ left: SIDEBAR_WIDTH + 12, top: tooltipPos.top, transform: 'translateY(-50%)' }}
        >
          {hovered}
        </div>
      )}
    </aside>
  );
}

export default memo(Sidebar);
