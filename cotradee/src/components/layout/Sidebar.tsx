import { memo, useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { SIDEBAR_WIDTH } from '@/utils/constants';

interface NavItem {
  path: string;
  icon: string;
  label: string;
  iconSize?: number;
}

const PRIMARY_NAV: NavItem[] = [
  { path: '/',         icon: '/assets/sidebar/icons/menu.svg',      label: 'Dashboard',     iconSize: 28 },
  { path: '/analysis', icon: '/assets/sidebar/icons/widget.svg',    label: 'Analysis',      iconSize: 28 },
  { path: '/trades',   icon: '/assets/sidebar/icons/Trade.svg',     label: 'Active Trades', iconSize: 28 },
  { path: '/journal',  icon: '/assets/sidebar/icons/analytics.svg', label: 'Journal',       iconSize: 28 },
];

const FOOTER_NAV: NavItem[] = [
  { path: '/settings', icon: '/assets/sidebar/icons/Setting-support.svg', label: 'Settings', iconSize: 28 },
  { path: '/support',  icon: '/assets/sidebar/icons/Setting-support.svg', label: 'Support',  iconSize: 28 },
];

interface SidebarProps {
  /** When true, the sidebar slides in over the page content (mobile drawer). */
  isMobileOpen?: boolean;
  /** Called when the user dismisses the mobile drawer. */
  onMobileClose?: () => void;
}

function Sidebar({ isMobileOpen = false, onMobileClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltipTop, setTooltipTop] = useState(0);

  const isActive = useCallback(
    (path: string) => (path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)),
    [location.pathname],
  );

  const handleMouseEnter = useCallback((label: string, e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setTooltipTop(rect.top + rect.height / 2);
    setHovered(label);
  }, []);

  // Close mobile drawer on route change.
  useEffect(() => {
    onMobileClose?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  // Lock body scroll while mobile drawer is open.
  useEffect(() => {
    if (!isMobileOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isMobileOpen]);

  const handleNavigate = (path: string) => {
    navigate(path);
    onMobileClose?.();
  };

  return (
    <>
      {/* Desktop rail */}
      <aside
        className="hidden md:flex fixed left-0 top-0 h-screen flex-col z-sidebar overflow-hidden
                   border-r border-border"
        style={{
          width: SIDEBAR_WIDTH,
          background: 'var(--gradient-sidebar)',
        }}
        aria-label="Primary navigation"
      >
        <RailContents
          isActive={isActive}
          onNavigate={handleNavigate}
          onHover={(label, e) => handleMouseEnter(label, e)}
          onLeave={() => setHovered(null)}
        />
        {hovered && (
          <div
            role="tooltip"
            className="fixed z-toast px-3 py-1.5 rounded-md text-xs font-medium text-content
                       bg-surface-elevated border border-border shadow-pop pointer-events-none"
            style={{
              left: SIDEBAR_WIDTH + 12,
              top: tooltipTop,
              transform: 'translateY(-50%)',
            }}
          >
            {hovered}
          </div>
        )}
      </aside>

      {/* Mobile drawer + scrim */}
      {isMobileOpen && (
        <>
          <div
            onClick={onMobileClose}
            className="md:hidden fixed inset-0 z-modal bg-black/55 animate-fade-in"
            aria-hidden
          />
          <aside
            className="md:hidden fixed left-0 top-0 h-screen flex flex-col z-modal overflow-hidden
                       border-r border-border animate-slide-right"
            style={{
              width: 220,
              background: 'var(--gradient-sidebar)',
            }}
            aria-label="Primary navigation"
          >
            {/* Logo + label header */}
            <div className="flex items-center gap-2 px-4 h-12 border-b border-border">
              <img
                src="/assets/sidebar/icons/logo.svg"
                alt=""
                width={28}
                height={28}
                className="select-none"
              />
              <span className="text-sm font-bold tracking-wide text-content">eTradie</span>
            </div>
            <nav className="flex-1 flex flex-col py-2 overflow-y-auto">
              {PRIMARY_NAV.map((item) => (
                <DrawerNavButton
                  key={item.path}
                  item={item}
                  active={isActive(item.path)}
                  onNavigate={handleNavigate}
                />
              ))}
            </nav>
            <div className="border-t border-border py-2">
              {FOOTER_NAV.map((item) => (
                <DrawerNavButton
                  key={item.path}
                  item={item}
                  active={isActive(item.path)}
                  onNavigate={handleNavigate}
                />
              ))}
            </div>
          </aside>
        </>
      )}
    </>
  );
}

function DrawerNavButton({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate: (p: string) => void;
}) {
  return (
    <button
      onClick={() => onNavigate(item.path)}
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 px-4 py-2.5 text-sm font-medium
                  transition-colors duration-fast border-l-2
                  ${
                    active
                      ? 'border-l-brand bg-brand-soft text-brand'
                      : 'border-l-transparent text-content-secondary hover:bg-surface-2 hover:text-content'
                  }`}
    >
      <img src={item.icon} alt="" width={22} height={22} className="select-none" />
      {item.label}
    </button>
  );
}

function RailContents({
  isActive,
  onNavigate,
  onHover,
  onLeave,
}: {
  isActive: (p: string) => boolean;
  onNavigate: (p: string) => void;
  onHover: (label: string, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  return (
    <>
      <button
        onClick={() => onNavigate('/')}
        className="flex items-center justify-center w-full h-12 mb-2 cursor-pointer focus-ring"
        aria-label="Home"
      >
        <img
          src="/assets/sidebar/icons/logo.svg"
          alt="eTradie"
          width={32}
          height={32}
          className="select-none"
        />
      </button>

      {/* Primary navigation — fills available vertical space. */}
      <nav className="flex flex-col flex-1" aria-label="Primary">
        {PRIMARY_NAV.map((item) => (
          <RailButton
            key={item.path}
            item={item}
            active={isActive(item.path)}
            onNavigate={onNavigate}
            onHover={onHover}
            onLeave={onLeave}
          />
        ))}
      </nav>

      {/* Footer navigation — anchored to the bottom of the rail. */}
      <div className="flex flex-col pt-2 pb-2 border-t border-border" aria-label="Account">
        {FOOTER_NAV.map((item) => (
          <RailButton
            key={item.path}
            item={item}
            active={isActive(item.path)}
            onNavigate={onNavigate}
            onHover={onHover}
            onLeave={onLeave}
          />
        ))}
      </div>
    </>
  );
}

function RailButton({
  item,
  active,
  onNavigate,
  onHover,
  onLeave,
}: {
  item: NavItem;
  active: boolean;
  onNavigate: (p: string) => void;
  onHover: (label: string, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  return (
    <button
      onClick={() => onNavigate(item.path)}
      onMouseEnter={(e) => onHover(item.label, e)}
      onMouseLeave={onLeave}
      aria-label={item.label}
      aria-current={active ? 'page' : undefined}
      className="relative flex items-center justify-center w-full h-12 mb-1
                 transition-all duration-fast cursor-pointer border-none bg-transparent focus-ring"
    >
      {active && (
        <>
          <span className="absolute left-0.5 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-brand rounded-full" />
          <span
            className="absolute inset-1.5 rounded-lg pointer-events-none bg-brand-soft"
            aria-hidden
          />
        </>
      )}
      <img
        src={item.icon}
        alt=""
        width={item.iconSize || 28}
        height={item.iconSize || 28}
        className="select-none transition-transform duration-fast relative z-[1]"
      />
    </button>
  );
}

export default memo(Sidebar);
