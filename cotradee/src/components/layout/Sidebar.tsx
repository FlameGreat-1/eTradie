import { memo, useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Zap,
  History,
  BookOpen,
  Settings,
  HelpCircle,
  Users,
  Box,
  ChevronRight,
} from 'lucide-react';
import { SIDEBAR_WIDTH } from '@/utils/constants';

interface NavItem {
  path?: string;
  icon: any;
  label: string;
  splitPaths?: { path: string; label: string }[];
}

const PRIMARY_NAV: NavItem[] = [
  { path: '/dashboard',                icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/dashboard/analysis',       icon: Zap,             label: 'Analysis' },
  { path: '/dashboard/trades',         icon: Box,             label: 'Active Trades' },
  { path: '/dashboard/journal',        icon: History,         label: 'Journal' },
  { path: '/dashboard/trading-system', icon: BookOpen,        label: 'Trading System' },
  { path: '/dashboard/community',      icon: Users,           label: 'Community' },
];

const FOOTER_NAV: NavItem[] = [
  { path: '/dashboard/settings', icon: Settings,   label: 'Settings' },
  { path: '/dashboard/support',  icon: HelpCircle, label: 'Support' },
];

interface SidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

function Sidebar({ isMobileOpen = false, onMobileClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltipTop, setTooltipTop] = useState(0);

  const isActive = useCallback(
    (path: string) => (path === '/dashboard' ? location.pathname === '/dashboard' : location.pathname.startsWith(path)),
    [location.pathname],
  );

  const handleMouseEnter = useCallback((label: string, e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setTooltipTop(rect.top + rect.height / 2);
    setHovered(label);
  }, []);

  useEffect(() => {
    onMobileClose?.();
  }, [location.pathname, onMobileClose]);

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
      <aside
        className="hidden md:flex fixed left-0 top-0 h-screen flex-col z-sidebar overflow-hidden
                   border-r border-black/10 dark:border-white/10 bg-white dark:bg-black shadow-2xl"
        style={{ width: SIDEBAR_WIDTH }}
        aria-label="Primary navigation"
      >
        <RailContents
          isActive={isActive}
          onNavigate={handleNavigate}
          onHover={handleMouseEnter}
          onLeave={() => setHovered(null)}
        />
        {hovered && (
          <div
            role="tooltip"
            className="fixed z-toast px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest text-black dark:text-white
                       bg-white/95 dark:bg-black/95 backdrop-blur-md border border-black/10 dark:border-white/10 shadow-2xl pointer-events-none animate-in fade-in slide-in-from-left-1 duration-300"
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

      {isMobileOpen && (
        <>
          <div
            onClick={onMobileClose}
            className="md:hidden fixed inset-0 z-modal bg-black/80 backdrop-blur-sm animate-in fade-in duration-500"
            aria-hidden
          />
          <aside
            className="md:hidden fixed left-0 top-0 h-screen flex flex-col z-modal overflow-hidden
                       border-r border-black/10 dark:border-white/10 bg-white dark:bg-black rounded-r-[2.5rem] shadow-2xl animate-in slide-in-from-left duration-500"
            style={{ width: 280 }}
            aria-label="Primary navigation"
          >
            <div className="flex items-center gap-3 px-8 h-16 border-b border-black/5 dark:border-white/5">
              <img src="/assets/sidebar/icons/logo.svg" alt="" width={32} height={32} />
              <span className="text-lg font-black tracking-tighter text-black dark:text-white uppercase">eTradie</span>
            </div>
            <nav className="flex-1 flex flex-col py-6 px-4 overflow-y-auto space-y-1">
              {PRIMARY_NAV.map((item) => (
                <DrawerNavButton
                  key={item.path}
                  item={item}
                  active={isActive(item.path || '')}
                  onNavigate={handleNavigate}
                />
              ))}
            </nav>
            <div className="border-t border-black/5 dark:border-white/5 p-4 space-y-1">
              {FOOTER_NAV.map((item, idx) => (
                <DrawerNavButton
                  key={item.path || idx}
                  item={item}
                  active={isActive(item.path || '')}
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
  const Icon = item.icon;

  return (
    <div className="relative">
      <div
        className={`flex items-center gap-4 px-6 py-4 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all duration-300
                    ${active
                      ? 'bg-black dark:bg-white text-white dark:text-black shadow-xl shadow-black/20 dark:shadow-white/20 translate-x-1'
                      : 'text-black/40 dark:text-white/40 hover:bg-black/5 dark:hover:bg-white/5'
                    }`}
      >
        <Icon size={18} strokeWidth={active ? 3 : 2} className="transition-all" />
        <span className="flex-1">{item.label}</span>
        {active && <ChevronRight size={14} strokeWidth={4} className="opacity-40" />}
      </div>

      <button
        onClick={() => onNavigate(item.path || '')}
        className="absolute inset-0 z-[2] bg-transparent border-none cursor-pointer focus-ring rounded-2xl"
        aria-label={item.label}
      />
    </div>
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
        onClick={() => onNavigate('/dashboard')}
        className="flex items-center justify-center w-full h-16 mb-4 cursor-pointer focus-ring group"
        aria-label="Home"
      >
        <img src="/assets/sidebar/icons/logo.svg" alt="eTradie" width={32} height={32} className="group-hover:scale-110 transition-transform duration-500" />
      </button>

      <nav className="flex flex-col flex-1 px-3 space-y-6" aria-label="Primary">
        {PRIMARY_NAV.map((item) => (
          <RailButton
            key={item.path}
            item={item}
            active={isActive(item.path || '')}
            onNavigate={onNavigate}
            onHover={onHover}
            onLeave={onLeave}
          />
        ))}
      </nav>

      <div className="flex flex-col pt-4 pb-6 px-3 space-y-6 border-t border-black/5 dark:border-white/5" aria-label="Account">
        {FOOTER_NAV.map((item) => (
          <RailButton
            key={item.path || item.label}
            item={item}
            active={isActive(item.path || '')}
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
  const Icon = item.icon;

  return (
    <div
      className="relative flex items-center justify-center w-full aspect-square group/rail"
      onMouseLeave={onLeave}
    >
      <div
        className={`w-full h-full rounded-2xl flex items-center justify-center transition-all duration-500
                    ${active
                      ? 'bg-black dark:bg-white text-white dark:text-black shadow-2xl shadow-black/20 dark:shadow-white/20'
                      : 'text-black/30 dark:text-white/30 hover:bg-black/5 dark:hover:bg-white/5'
                    }`}
      >
        <Icon size={22} strokeWidth={active ? 3 : 2} className="transition-all" />
      </div>

      <button
        onClick={() => item.path && onNavigate(item.path)}
        onMouseEnter={(e) => onHover(item.label, e)}
        className="absolute inset-0 z-[2] bg-transparent border-none cursor-pointer focus-ring rounded-2xl"
        aria-label={item.label}
      />
    </div>
  );
}

export default memo(Sidebar);
