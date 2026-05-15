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
  ChevronLeft,
} from 'lucide-react';
import { SIDEBAR_WIDTH } from '@/utils/constants';

const EXPANDED_WIDTH = 200;
const COLLAPSED_WIDTH = 48;

interface NavItem {
  path?: string;
  icon: any;
  label: string;
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
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltipTop, setTooltipTop] = useState(0);

  useEffect(() => {
    const width = isCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;
    document.documentElement.style.setProperty('--sidebar-width', `${width}px`);
  }, [isCollapsed]);

  const isActive = useCallback(
    (path: string) => (path === '/dashboard' ? location.pathname === '/dashboard' : location.pathname.startsWith(path)),
    [location.pathname],
  );

  const handleMouseEnter = useCallback((label: string, e: React.MouseEvent) => {
    if (!isCollapsed) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setTooltipTop(rect.top + rect.height / 2);
    setHovered(label);
  }, [isCollapsed]);

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
        className={`hidden md:flex fixed left-0 top-0 h-screen flex-col z-sidebar transition-all duration-300 ease-out
                   border-r border-black/10 dark:border-white/10 bg-white dark:bg-black shadow-2xl`}
        style={{ width: isCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH }}
        aria-label="Primary navigation"
      >
        <SidebarContents
          isCollapsed={isCollapsed}
          isActive={isActive}
          onNavigate={handleNavigate}
          onHover={handleMouseEnter}
          onLeave={() => setHovered(null)}
        />

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-2.5 top-1/2 -translate-y-1/2 z-modal
                     flex items-center justify-center w-5 h-5 rounded-full
                     bg-white dark:bg-white text-black dark:text-black
                     border border-black/10 dark:border-black/10 shadow-xl
                     hover:scale-110 active:scale-95 transition-all group/toggle"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight size={12} strokeWidth={3} className="group-hover/toggle:translate-x-0.5 transition-transform" />
          ) : (
            <ChevronLeft size={12} strokeWidth={3} className="group-hover/toggle:-translate-x-0.5 transition-transform" />
          )}
        </button>

        {isCollapsed && hovered && (
          <div
            role="tooltip"
            className="fixed z-toast px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest text-black dark:text-white
                       bg-white/95 dark:bg-black/95 backdrop-blur-md border border-black/10 dark:border-white/10 shadow-2xl pointer-events-none animate-in fade-in slide-in-from-left-1 duration-300"
            style={{
              left: COLLAPSED_WIDTH + 12,
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
              <span className="text-lg font-bold tracking-tight text-black dark:text-white">Exoper</span>
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
        className={`flex items-center gap-4 px-6 py-4 rounded-2xl text-[13px] font-bold transition-all duration-300
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

function SidebarContents({
  isCollapsed,
  isActive,
  onNavigate,
  onHover,
  onLeave,
}: {
  isCollapsed: boolean;
  isActive: (p: string) => boolean;
  onNavigate: (p: string) => void;
  onHover: (label: string, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  return (
    <>
      <button
        onClick={() => onNavigate('/dashboard')}
        className={`flex items-center ${isCollapsed ? 'justify-center' : 'px-6'} w-full h-16 mb-2 cursor-pointer focus-ring group transition-all`}
        aria-label="Home"
      >
        <img
          src="/assets/sidebar/icons/logo.svg"
          alt="eTradie"
          width={32}
          height={32}
          className="group-hover:scale-110 transition-transform duration-500 shrink-0"
        />
        {!isCollapsed && (
          <span className="ml-3 text-lg font-bold tracking-tight text-black dark:text-white">
            Exoper
          </span>
        )}
      </button>

      <nav className={`flex flex-col flex-1 ${isCollapsed ? 'px-1.5' : 'px-3'} space-y-1 overflow-x-hidden`} aria-label="Primary">
        {PRIMARY_NAV.map((item) => (
          <SidebarButton
            key={item.path}
            item={item}
            isCollapsed={isCollapsed}
            active={isActive(item.path || '')}
            onNavigate={onNavigate}
            onHover={onHover}
            onLeave={onLeave}
          />
        ))}
      </nav>

      <div className={`flex flex-col pt-4 pb-6 ${isCollapsed ? 'px-1.5' : 'px-3'} space-y-1 border-t border-black/5 dark:border-white/5 overflow-x-hidden`} aria-label="Account">
        {FOOTER_NAV.map((item) => (
          <SidebarButton
            key={item.path || item.label}
            item={item}
            isCollapsed={isCollapsed}
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

function SidebarButton({
  item,
  isCollapsed,
  active,
  onNavigate,
  onHover,
  onLeave,
}: {
  item: NavItem;
  isCollapsed: boolean;
  active: boolean;
  onNavigate: (p: string) => void;
  onHover: (label: string, e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  const Icon = item.icon;

  return (
    <div
      className="relative flex items-center w-full group/nav"
      onMouseLeave={onLeave}
    >
      <div
        className={`w-full rounded-2xl flex items-center transition-all duration-300
                    ${isCollapsed ? 'justify-center aspect-square' : 'px-4 py-3 gap-4'}
                    ${active
                      ? 'bg-black dark:bg-white text-white dark:text-black shadow-2xl shadow-black/20 dark:shadow-white/20'
                      : 'text-black/30 dark:text-white/30 hover:bg-black/5 dark:hover:bg-white/5'
                    }`}
      >
        <Icon size={20} strokeWidth={active ? 3 : 2} className="transition-all shrink-0" />
        {!isCollapsed && (
          <span className="text-[13px] font-bold truncate flex-1">
            {item.label}
          </span>
        )}
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
