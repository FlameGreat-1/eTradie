import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import { useTheme } from '@/providers/ThemeProvider';
import { useBrokerAccount } from '@/features/execution/api/brokerAccount';
import { formatCurrency } from '@/utils/formatters';
import { SIDEBAR_WIDTH } from '@/utils/constants';
import { Moon, Sun, Bell, ChevronDown, Search, LogOut, Zap } from 'lucide-react';
import { useRunCycle } from '@/features/analysis/api/analysis';

function Header() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const { data: account } = useBrokerAccount();
  const runCycle = useRunCycle();

  const [time, setTime] = useState(new Date());
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    if (showUserMenu) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showUserMenu]);

  const fmtTime = useCallback((d: Date) => {
    return d.toLocaleTimeString('en-US', { hour12: false });
  }, []);

  const tzOffset = useCallback(() => {
    const off = -new Date().getTimezoneOffset() / 60;
    return off >= 0 ? `(+${off})` : `(${off})`;
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  return (
    <header
      className="fixed top-0 z-header h-header overflow-visible"
      style={{
        left: SIDEBAR_WIDTH,
        right: 0,
        background: 'linear-gradient(90deg, var(--surface-3) 0%, var(--surface-2) 50%, var(--surface-3) 100%)',
      }}
    >
      <div className="relative w-full h-full flex items-center justify-between px-3">
        {/* Left: Stats */}
        <div className="hidden md:flex items-center gap-2.5">
          <StatItem label="Balance" value={account ? formatCurrency(account.balance) : '---'} />
          <Divider />
          <StatItem label="Equity" value={account ? formatCurrency(account.equity) : '---'} />
          <Divider />
          <StatItem label="Margin" value={account ? formatCurrency(account.margin) : '---'} />
          <Divider />
          <StatItem label="Margin Free" value={account ? formatCurrency(account.margin_free) : '---'} />
          <Divider />
          <StatItem
            label="Margin Level"
            value={account ? formatMarginLevel(account.equity, account.margin) : '---'}
            valueClass={account ? marginLevelClass(account.equity, account.margin) : undefined}
          />
          <Divider />
          <StatItem label="Time Zone" value={`${fmtTime(time)} ${tzOffset()}`} />
          <Divider />

          {/* Search */}
          <div className="flex items-center gap-1.5 rounded-full bg-surface-2 border border-border px-3 h-8">
            <Search size={14} className="text-content-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search…"
              className="bg-transparent border-none outline-none text-xs text-content placeholder:text-content-muted w-28"
            />
          </div>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Run Full Scan */}
          <button
            title="Run Analysis Scan"
            onClick={() => runCycle.mutate(undefined)}
            disabled={runCycle.isPending}
            className="flex items-center justify-center w-8 h-8 rounded-full
                       bg-surface-2 border border-border hover:border-brand transition-colors
                       disabled:opacity-50 disabled:hover:border-border"
          >
            <Zap size={14} className={runCycle.isPending ? "animate-pulse text-brand" : "text-content"} />
          </button>

          {/* Theme toggle */}
          <button
            title="Toggle Theme"
            onClick={toggleTheme}
            className="flex items-center justify-center w-8 h-8 rounded-full
                       bg-surface-2 border border-border hover:border-brand transition-colors"
          >
            {theme === 'dark' ? <Sun size={14} className="text-content" /> : <Moon size={14} className="text-content" />}
          </button>

          {/* Notifications */}
          <button
            title="View Notifications"
            onClick={() => navigate('/notifications')}
            className="relative flex items-center justify-center w-8 h-8 rounded-full
                       bg-surface-2 border border-border hover:border-brand transition-colors"
          >
            <Bell size={14} className="text-content" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-brand" />
          </button>

          {/* User pill */}
          <div className="relative" ref={menuRef}>
            <button
              title="User Menu"
              onClick={() => setShowUserMenu((p) => !p)}
              className="flex items-center gap-2 rounded-full bg-surface-2 border border-border
                         px-2 h-9 hover:border-brand transition-colors"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand/20 to-brand/60 flex items-center justify-center text-xs font-bold text-white">
                {user?.username?.charAt(0).toUpperCase() || '?'}
              </div>
              <div className="hidden sm:flex flex-col items-start">
                <span className="text-xs font-medium text-content leading-none">{user?.username || 'User'}</span>
                <span className="text-[10px] text-content-muted leading-none">{user?.role || ''}</span>
              </div>
              <ChevronDown size={12} className="text-content-muted" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 top-11 w-48 rounded-lg bg-surface-2 border border-border shadow-dropdown animate-fade-in z-50">
                <button
                  onClick={() => { navigate('/settings/profile'); setShowUserMenu(false); }}
                  className="w-full text-left px-4 py-2.5 text-xs text-content hover:bg-surface-3 transition-colors rounded-t-lg"
                >
                  My Profile
                </button>
                <button
                  onClick={() => { navigate('/settings'); setShowUserMenu(false); }}
                  className="w-full text-left px-4 py-2.5 text-xs text-content hover:bg-surface-3 transition-colors"
                >
                  Settings
                </button>
                <div className="border-t border-border" />
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2.5 text-xs text-danger hover:bg-surface-3 transition-colors rounded-b-lg flex items-center gap-2"
                >
                  <LogOut size={12} /> Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

function StatItem({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold text-content-muted uppercase tracking-wide select-none">{label}</span>
      <span className={`text-[11px] font-bold whitespace-nowrap ${valueClass ?? 'text-content'}`}>{value}</span>
    </div>
  );
}

// Margin Level % = (Equity / Margin) * 100. When no positions are open
// Margin is 0 and the ratio is mathematically undefined; MT5 and every
// retail broker renders that case as a healthy infinity.
function formatMarginLevel(equity: number | undefined, margin: number | undefined): string {
  if (equity == null || margin == null) return '---';
  if (margin <= 0) return '∞';
  const pct = (equity / margin) * 100;
  if (!Number.isFinite(pct)) return '∞';
  return `${pct.toFixed(2)}%`;
}

// Standard broker thresholds. >= 300% is healthy, 100-300% is caution,
// below 100% is margin-call territory and the broker begins forced
// liquidations.
function marginLevelClass(equity: number | undefined, margin: number | undefined): string {
  if (equity == null || margin == null) return 'text-content';
  if (margin <= 0) return 'text-success';
  const pct = (equity / margin) * 100;
  if (!Number.isFinite(pct)) return 'text-success';
  if (pct < 100) return 'text-danger';
  if (pct < 300) return 'text-warning';
  return 'text-success';
}

function Divider() {
  return <div className="w-px h-7 bg-gradient-to-b from-transparent via-border to-transparent flex-shrink-0" />;
}

export default memo(Header);
