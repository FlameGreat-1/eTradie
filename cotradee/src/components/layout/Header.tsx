import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import { useConsentOptional } from '@/features/consent/useConsent';
import { useTheme } from '@/providers/ThemeProvider';
import { useBrokerAccount } from '@/features/execution/api/brokerAccount';
import { formatCurrency } from '@/utils/formatters';
import { SIDEBAR_WIDTH } from '@/utils/constants';
import {
  Moon,
  Sun,
  ChevronDown,
  Search,
  LogOut,
  Zap,
  Activity,
  Menu,
  X,
} from 'lucide-react';
import { useRunCycle } from '@/features/analysis/api/analysis';
import { TimeframeDropdown } from '@/features/chart/components/TimeframeDropdown';
import { SymbolSearchModal } from '@/features/chart/components/SymbolSearchModal';
import { NotificationsPanel } from '@/features/alerts/components/NotificationsPanel';

// localStorage keys used by this component are UI PREFERENCES ONLY.
// They persist the user's last-selected trading pair and timeframe so
// re-entering the dashboard does not feel jarring. No authentication
// token, refresh token, or anything else security-sensitive is ever
// written under these keys — those live in HttpOnly cookies set by
// the gateway and are unreadable from JS (see docs/cookie-auth.md).
const SYMBOL_KEY = 'active_symbol';
const TF_KEY = 'active_tf';

interface HeaderProps {
  /**
   * When provided, the mobile hamburger trigger is rendered inside
   * the header (md:hidden) and this callback fires on click. Pass
   * `undefined` to suppress the trigger (e.g. on auth screens).
   */
  onMenuClick?: () => void;
}

function StatGroup({
  account,
  time,
  fmtTime,
  tzOffset,
  withDividers = true,
}: {
  account: any;
  time: Date;
  fmtTime: (d: Date) => string;
  tzOffset: () => string;
  withDividers?: boolean;
}) {
  return (
    <>
      <StatItem label="Balance" value={account ? formatCurrency(account.balance) : '---'} />
      {withDividers && <Divider />}
      <StatItem label="Equity" value={account ? formatCurrency(account.equity) : '---'} />
      {withDividers && <Divider />}
      <StatItem label="Margin" value={account ? formatCurrency(account.margin) : '---'} />
      {withDividers && <Divider />}
      <StatItem label="Free" value={account ? formatCurrency(account.margin_free) : '---'} />
      {withDividers && <Divider />}
      <StatItem
        label="M. Level"
        value={account ? formatMarginLevel(account.equity, account.margin) : '---'}
        valueClass={account ? marginLevelClass(account.equity, account.margin) : undefined}
      />
      {withDividers && <Divider />}
      <StatItem label="Time" value={`${fmtTime(time)} ${tzOffset()}`} />
    </>
  );
}

function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth();
  // Optional so the header degrades gracefully if it is ever
  // rendered outside ConsentProvider. PRACTICE.md #7 requires every
  // authenticated surface to expose a one-click route to the cookie
  // preferences modal to satisfy GDPR Art. 7.3.
  const consent = useConsentOptional();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: account } = useBrokerAccount();
  const runCycle = useRunCycle();

  const [time, setTime] = useState(new Date());
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showStatsDrawer, setShowStatsDrawer] = useState(false);
  const [isSymbolModalOpen, setIsSymbolModalOpen] = useState(false);
  const [userMenuCoords, setUserMenuCoords] = useState({ top: 0, right: 0 });
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const desktopMenuRef = useRef<HTMLDivElement>(null);
  const userPortalRef = useRef<HTMLDivElement>(null);

  const toggleUserMenu = () => {
    if (!showUserMenu) {
      const activeRef = window.innerWidth < 768 ? mobileMenuRef : desktopMenuRef;
      if (activeRef.current) {
        const rect = activeRef.current.getBoundingClientRect();
        setUserMenuCoords({
          top: rect.bottom + window.scrollY,
          right: window.innerWidth - rect.right - window.scrollX,
        });
      }
    }
    setShowUserMenu(!showUserMenu);
  };

  const onDashboard = location.pathname === '/dashboard';
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
      const target = e.target as Node;
      const activeRef = window.innerWidth < 768 ? mobileMenuRef : desktopMenuRef;
      
      const clickedOutsideTrigger = activeRef.current && !activeRef.current.contains(target);
      const clickedOutsidePortal = userPortalRef.current && !userPortalRef.current.contains(target);

      if (clickedOutsideTrigger && clickedOutsidePortal) {
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
        left: 'var(--header-left, 0px)',
        right: 0,
        height: 'var(--header-height)',
        background: 'var(--gradient-header)',
      }}
      role="banner"
    >
      {/* Header sits flush against the desktop rail (>=md) and full-width on mobile. */}
      <style>{`
        @media (min-width: 768px) {
          :root { --header-left: ${SIDEBAR_WIDTH}px; }
        }
        @media (max-width: 767.98px) {
          :root { --header-left: 0px; }
        }
      `}</style>

      <div className="relative w-full h-full flex items-center justify-between gap-2 px-2 sm:px-3">
        {/* Mobile-only: hamburger + stats-drawer toggle, anchored to the left of the bar. */}
        <div className="flex md:hidden items-center gap-1.5 shrink-0">
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="flex items-center justify-center w-9 h-9 rounded-md
                         bg-surface-2 border border-border text-content focus-ring
                         transition-colors duration-fast hover:border-brand"
              aria-label="Open navigation menu"
            >
              <Menu size={16} />
            </button>
          )}
          <button
            onClick={() => setShowStatsDrawer((p) => !p)}
            className="flex items-center justify-center w-9 h-9 rounded-md
                       bg-surface-2 border border-border text-content focus-ring
                       transition-colors duration-fast hover:border-brand"
            aria-label="Toggle account stats"
            aria-expanded={showStatsDrawer}
          >
            <Activity size={16} />
          </button>
        </div>

        {/* Swipeable container for Symbol, TF, and Actions (Mobile) */}
        <div className="flex md:hidden items-center gap-2 flex-1 min-w-0 overflow-x-auto no-scrollbar py-1 pr-2">
          <div className="flex items-center gap-1.5 shrink-0">
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

          <Divider />

          <div className="flex items-center gap-1.5 shrink-0">
            <IconButton
              title="Run analysis"
              onClick={() => runCycle.mutate(undefined)}
              disabled={runCycle.isPending}
              className="!w-8 !h-8"
            >
              <Zap
                size={14}
                className={runCycle.isPending ? 'animate-pulse text-brand' : 'text-content'}
              />
            </IconButton>
            <IconButton title="Toggle theme" onClick={toggleTheme} className="!w-8 !h-8">
              {theme === 'dark'
                ? <Sun size={14} className="text-content" />
                : <Moon size={14} className="text-content" />}
            </IconButton>
            <NotificationsPanel />
            
            {/* User pill*/}
            <div className="relative shrink-0" ref={mobileMenuRef}>
              <button
                onClick={toggleUserMenu}
                className="flex items-center gap-2 rounded-full bg-surface-2 border border-border
                           px-2 h-9 hover:border-brand transition-colors duration-fast focus-ring"
              >
                <img src="/assets/dashboard/icons/profilePic.png" alt={user?.username || 'Profile'} className="w-7 h-7 rounded-full object-cover" />
                <ChevronDown size={12} className="text-content-muted" />
              </button>
            </div>
          </div>
        </div>

        {/* Desktop: stats strip + non-scrollable controls. */}
        <div className="hidden md:flex items-center gap-2.5 min-w-0 flex-1">
          <div className="flex items-center gap-2.5 min-w-0 overflow-x-auto no-scrollbar">
            <StatGroup account={account} time={time} fmtTime={fmtTime} tzOffset={tzOffset} />
          </div>

          <Divider />

          <div className="flex items-center gap-2.5 flex-shrink-0">
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

            <div className="hidden lg:flex items-center gap-1.5 rounded-full bg-surface-2 border border-border px-3 h-8">
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
        </div>


        {/* Right: action buttons (Desktop only, now integrated in swipe area for mobile) */}
        <div className="hidden md:flex items-center gap-1.5 sm:gap-2 ml-auto flex-shrink-0">
          <IconButton
            title="Run analysis"
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
          <NotificationsPanel />

          {/* User pill */}
          <div className="relative" ref={desktopMenuRef}>
            <button
              title="User menu"
              onClick={toggleUserMenu}
              className="flex items-center gap-2 rounded-full bg-surface-2 border border-border
                         px-2 h-9 hover:border-brand transition-colors duration-fast focus-ring"
              aria-haspopup="menu"
              aria-expanded={showUserMenu}
            >
              <img src="/assets/dashboard/icons/profilePic.png" alt={user?.username || 'Profile'} className="w-7 h-7 rounded-full object-cover" />
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
          </div>
        </div>
      </div>

      {showUserMenu && createPortal(
        <div
          ref={userPortalRef}
          role="menu"
          style={{
            position: 'fixed',
            top: `${userMenuCoords.top + 8}px`,
            right: `${userMenuCoords.right}px`,
          }}
          className="w-48 rounded-lg bg-surface-elevated border border-border
                     shadow-pop animate-fade-in z-portal"
        >
          <MenuItem onClick={() => { navigate('/dashboard/settings/profile'); setShowUserMenu(false); }}>
            My Profile
          </MenuItem>
          <MenuItem onClick={() => { navigate('/dashboard/settings'); setShowUserMenu(false); }}>
            Settings
          </MenuItem>
          {consent && (
            <MenuItem
              onClick={() => {
                consent.openPreferences();
                setShowUserMenu(false);
              }}
            >
              Cookie Preferences
            </MenuItem>
          )}
          <div className="border-t border-border" />
          <MenuItem onClick={handleLogout} danger>
            <LogOut size={12} /> Sign out
          </MenuItem>
        </div>,
        document.body
      )}

      {/* Mobile stats drawer (Restored) */}
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
            <StatGroup account={account} time={time} fmtTime={fmtTime} tzOffset={tzOffset} withDividers={false} />
          </div>
        </div>
      )}


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
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[10px] font-semibold text-content-muted uppercase tracking-wide select-none">
        {label}
      </span>
      <span
        className={`text-[11px] font-bold whitespace-nowrap ${valueClass ?? 'text-content'}`}
      >
        {value}
      </span>
    </div>
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
