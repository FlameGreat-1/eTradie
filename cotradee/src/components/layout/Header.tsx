import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import { useTheme } from '@/providers/ThemeProvider';
import { useBrokerAccount } from '@/features/execution/api/brokerAccount';
import { useRealtime } from '@/features/realtime';
import { formatCurrency } from '@/utils/formatters';
import { SIDEBAR_WIDTH } from '@/utils/constants';
import {
  Moon,
  Sun,
  Bell,
  ChevronDown,
  Search,
  LogOut,
  Zap,
  Activity,
  X,
} from 'lucide-react';
import { useRunCycle } from '@/features/analysis/api/analysis';
import { TimeframeDropdown } from '@/features/chart/components/TimeframeDropdown';
import { SymbolSearchModal } from '@/features/chart/components/SymbolSearchModal';

const SYMBOL_KEY = 'active_symbol';
const TF_KEY = 'active_tf';

// How long the connection must stay down before we surface anything
// to the user. Anything shorter is silent: page-mount handshakes,
// short network blips, and routine reconnects should NOT alarm the
// trader.
const DEGRADED_GRACE_MS = 10_000;

function Header() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: account } = useBrokerAccount();
  const { isConnected } = useRealtime();
  const runCycle = useRunCycle();

  const [time, setTime] = useState(new Date());
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showStatsDrawer, setShowStatsDrawer] = useState(false);
  const [isSymbolModalOpen, setIsSymbolModalOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const onDashboard = location.pathname === '/';
  const [persistedSymbol, setPersistedSymbol] = useState(
    () => localStorage.getItem(SYMBOL_KEY) || '',
  );
  const [persistedTf, setPersistedTf] = useState(
    () => localStorage.getItem(TF_KEY) || 'H1',
  );

  const symbol = searchParams.get('symbol') || persistedSymbol;
  const timeframe = searchParams.get('tf') || persistedTf;

  useEffect(() => {
    const sp = searchParams.get('symbol');
    const tp = searchParams.get('tf');
    if (sp && sp !== persistedSymbol) {
      localStorage.setItem(SYMBOL_KEY, sp);
      setPersistedSymbol(sp);
    }
    if (tp && tp !== persistedTf) {
      localStorage.setItem(TF_KEY, tp);
      setPersistedTf(tp);
    }
  }, [searchParams, persistedSymbol, persistedTf]);

  const updateActive = useCallback(
    (newSymbol?: string, newTf?: string) => {
      if (newSymbol) {
        localStorage.setItem(SYMBOL_KEY, newSymbol);
        setPersistedSymbol(newSymbol);
      }
      if (newTf) {
        localStorage.setItem(TF_KEY, newTf);
        setPersistedTf(newTf);
      }
      if (onDashboard) {
        const params = new URLSearchParams(searchParams);
        if (newSymbol) params.set('symbol', newSymbol);
        if (newTf) params.set('tf', newTf);
        setSearchParams(params, { replace: true });
      } else if (newSymbol || newTf) {
        const params = new URLSearchParams();
        params.set('symbol', newSymbol || persistedSymbol);
        params.set('tf', newTf || persistedTf);
        navigate(`/?${params.toString()}`);
      }
    },
    [onDashboard, searchParams, setSearchParams, navigate, persistedSymbol, persistedTf],
  );

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

  const fmtTime = useCallback(
    (d: Date) => d.toLocaleTimeString('en-US', { hour12: false }),
    [],
  );
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
      className="fixed top-0 z-header overflow-visible border-b border-border"
      style={{
        left: SIDEBAR_WIDTH,
        right: 0,
        height: 'var(--header-height)',
        background: 'var(--gradient-header)',
      }}
      role="banner"
    >
      <div className="relative w-full h-full flex items-center justify-between gap-2 px-2 sm:px-3">
        {/* Mobile: stats drawer toggle */}
        <button
          onClick={() => setShowStatsDrawer((p) => !p)}
          className="md:hidden flex items-center justify-center w-9 h-9 rounded-md
                     bg-surface-2 border border-border text-content focus-ring
                     transition-colors duration-fast hover:border-brand"
          aria-label="Toggle account stats"
          aria-expanded={showStatsDrawer}
        >
          <Activity size={16} />
        </button>

        {/* Desktop: full stats strip */}
        <div className="hidden md:flex items-center gap-2.5 min-w-0 overflow-x-auto no-scrollbar">
          <StatItem label="Balance" value={account ? formatCurrency(account.balance) : '---'} />
          <Divider />
          <StatItem label="Equity" value={account ? formatCurrency(account.equity) : '---'} />
          <Divider />
          <StatItem label="Margin" value={account ? formatCurrency(account.margin) : '---'} />
          <Divider />
          <StatItem
            label="Free"
            value={account ? formatCurrency(account.margin_free) : '---'}
          />
          <Divider />
          <StatItem
            label="M. Level"
            value={account ? formatMarginLevel(account.equity, account.margin) : '---'}
            valueClass={account ? marginLevelClass(account.equity, account.margin) : undefined}
          />
          <Divider />
          <StatItem
            label="Time"
            value={`${fmtTime(time)} ${tzOffset()}`}
            accessory={<DegradedIndicator connected={isConnected} />}
          />
          <Divider />

          {/* Symbol + timeframe */}
          <button
            onClick={() => setIsSymbolModalOpen(true)}
            className="px-3 h-8 rounded-md text-xs font-bold text-content border border-border
                       hover:bg-surface-3 transition-colors duration-fast flex items-center gap-2 focus-ring"
          >
            {symbol || 'Select Symbol'}
            <ChevronDown size={14} className="text-content-muted" />
          </button>
          <TimeframeDropdown
            value={timeframe}
            onChange={(tf) => updateActive(undefined, tf)}
          />

          {/* Search */}
          <div className="flex items-center gap-1.5 rounded-full bg-surface-2 border border-border px-3 h-8">
            <Search size={14} className="text-content-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search…"
              className="bg-transparent border-none outline-none text-xs text-content placeholder:text-content-muted w-24"
              aria-label="Search"
            />
          </div>
        </div>

        {/* Mobile: compact symbol + tf */}
        <div className="flex md:hidden items-center gap-1.5">
          <button
            onClick={() => setIsSymbolModalOpen(true)}
            className="px-2 h-8 rounded-md text-xs font-bold text-content border border-border
                       hover:bg-surface-3 transition-colors duration-fast flex items-center gap-1.5 focus-ring max-w-[120px] truncate"
          >
            <span className="truncate">{symbol || 'Symbol'}</span>
            <ChevronDown size={12} className="text-content-muted shrink-0" />
          </button>
          <TimeframeDropdown
            value={timeframe}
            onChange={(tf) => updateActive(undefined, tf)}
          />
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2 ml-auto">
          <IconButton
            title="Run analysis scan"
            onClick={() => runCycle.mutate(undefined)}
            disabled={runCycle.isPending}
          >
            <Zap
              size={14}
              className={runCycle.isPending ? 'animate-pulse text-brand' : 'text-content'}
            />
          </IconButton>
          <IconButton title="Toggle theme" onClick={toggleTheme}>
            {theme === 'dark'
              ? <Sun size={14} className="text-content" />
              : <Moon size={14} className="text-content" />}
          </IconButton>
          <IconButton
            title="Notifications"
            onClick={() => navigate('/notifications')}
            className="relative"
          >
            <Bell size={14} className="text-content" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-brand" />
          </IconButton>

          {/* User pill */}
          <div className="relative" ref={menuRef}>
            <button
              title="User menu"
              onClick={() => setShowUserMenu((p) => !p)}
              className="flex items-center gap-2 rounded-full bg-surface-2 border border-border
                         px-2 h-9 hover:border-brand transition-colors duration-fast focus-ring"
              aria-haspopup="menu"
              aria-expanded={showUserMenu}
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-soft to-brand flex items-center justify-center text-[11px] font-bold text-strong">
                {user?.username?.charAt(0).toUpperCase() || '?'}
              </div>
              <div className="hidden sm:flex flex-col items-start">
                <span className="text-xs font-medium text-content leading-none">
                  {user?.username || 'User'}
                </span>
                <span className="text-[10px] text-content-muted leading-none">
                  {user?.role || ''}
                </span>
              </div>
              <ChevronDown size={12} className="text-content-muted" />
            </button>

            {showUserMenu && (
              <div
                role="menu"
                className="absolute right-0 top-11 w-48 rounded-lg bg-surface-elevated border border-border
                           shadow-pop animate-fade-in z-dropdown"
              >
                <MenuItem onClick={() => { navigate('/settings/profile'); setShowUserMenu(false); }}>
                  My Profile
                </MenuItem>
                <MenuItem onClick={() => { navigate('/settings'); setShowUserMenu(false); }}>
                  Settings
                </MenuItem>
                <div className="border-t border-border" />
                <MenuItem onClick={handleLogout} danger>
                  <LogOut size={12} /> Sign out
                </MenuItem>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile stats drawer */}
      {showStatsDrawer && (
        <div className="md:hidden fixed inset-x-0 top-[var(--header-height)] z-dropdown
                        bg-surface-1 border-b border-border shadow-pop animate-slide-up">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <span className="text-xs font-bold uppercase tracking-wider text-content-muted">
              Account
            </span>
            <button
              onClick={() => setShowStatsDrawer(false)}
              className="text-content-muted hover:text-content focus-ring rounded-md p-1"
              aria-label="Close stats"
            >
              <X size={14} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3 p-4">
            <StatItem label="Balance"  value={account ? formatCurrency(account.balance) : '---'} />
            <StatItem label="Equity"   value={account ? formatCurrency(account.equity) : '---'} />
            <StatItem label="Margin"   value={account ? formatCurrency(account.margin) : '---'} />
            <StatItem label="Free"     value={account ? formatCurrency(account.margin_free) : '---'} />
            <StatItem
              label="M. Level"
              value={account ? formatMarginLevel(account.equity, account.margin) : '---'}
              valueClass={account ? marginLevelClass(account.equity, account.margin) : undefined}
            />
            <StatItem label="Time" value={`${fmtTime(time)} ${tzOffset()}`} />
          </div>
        </div>
      )}

      {/* Symbol search modal */}
      <SymbolSearchModal
        isOpen={isSymbolModalOpen}
        onClose={() => setIsSymbolModalOpen(false)}
        onSelect={(sym) => {
          updateActive(sym, undefined);
          setIsSymbolModalOpen(false);
        }}
      />
    </header>
  );
}

function StatItem({
  label,
  value,
  valueClass,
  accessory,
}: {
  label: string;
  value: string;
  valueClass?: string;
  accessory?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[10px] font-semibold text-content-muted uppercase tracking-wide select-none">
        {label}
      </span>
      <span
        className={`flex items-center gap-1.5 text-[11px] font-bold whitespace-nowrap ${
          valueClass ?? 'text-content'
        }`}
      >
        {value}
        {accessory}
      </span>
    </div>
  );
}

/**
 * Discreet connection indicator.
 *
 *   connected            -> a tiny green dot, no text (silent success).
 *   disconnected < 10 s  -> renders nothing (silent grace window).
 *   disconnected ≥ 10 s  -> small amber dot + "Offline" label.
 *
 * Data still flows during "Offline" because the polling fallback is
 * in charge; the indicator only tells the trader the push channel
 * is degraded.
 */
function DegradedIndicator({ connected }: { connected: boolean }) {
  const [degraded, setDegraded] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (connected) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (degraded) setDegraded(false);
      return;
    }
    // Disconnected: start (or keep) the grace timer.
    if (timerRef.current) return;
    timerRef.current = setTimeout(() => {
      setDegraded(true);
      timerRef.current = null;
    }, DEGRADED_GRACE_MS);
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [connected, degraded]);

  if (connected) {
    return (
      <span
        className="inline-block w-1.5 h-1.5 rounded-full bg-success"
        title="Live data"
        aria-label="Live data"
      />
    );
  }

  if (!degraded) return null;

  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-semibold text-warning"
      title="Real-time push channel offline. Data is still updating via polling."
      aria-label="Real-time push channel offline"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-warning" />
      Offline
    </span>
  );
}

function IconButton({
  children,
  title,
  onClick,
  disabled,
  className,
}: {
  children: React.ReactNode;
  title: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center w-9 h-9 rounded-full
                  bg-surface-2 border border-border hover:border-brand transition-colors duration-fast
                  disabled:opacity-50 disabled:hover:border-border focus-ring ${className ?? ''}`}
    >
      {children}
    </button>
  );
}

function MenuItem({
  children,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-2.5 text-xs transition-colors duration-fast
                  flex items-center gap-2 first:rounded-t-lg last:rounded-b-lg
                  ${
                    danger
                      ? 'text-danger hover:bg-danger-soft'
                      : 'text-content hover:bg-surface-3'
                  }`}
      role="menuitem"
    >
      {children}
    </button>
  );
}

function formatMarginLevel(equity: number | undefined, margin: number | undefined): string {
  if (equity == null || margin == null) return '---';
  if (margin <= 0) return '∞';
  const pct = (equity / margin) * 100;
  if (!Number.isFinite(pct)) return '∞';
  return `${pct.toFixed(2)}%`;
}

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
  return (
    <div
      className="w-px h-7 bg-gradient-to-b from-transparent via-border to-transparent flex-shrink-0"
      aria-hidden
    />
  );
}

export default memo(Header);
