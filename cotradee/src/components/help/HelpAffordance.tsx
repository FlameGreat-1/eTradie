import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MessageSquarePlus, Inbox, Users, X, BookOpen, HelpCircle } from 'lucide-react';
import { useAuth } from '@/features/auth';

/**
 * Routes on which the floating help widget is intentionally hidden so
 * it does not clash with chrome that is deliberately minimal.
 *
 * Kept as a pure predicate over the pathname so the rule is:
 *   - greppable in one place
 *   - unit-testable without React
 *   - cheap to evaluate on every navigation (no regex compilation)
 *
 * Order matters: more-specific prefixes appear first so the
 * decision is correct for nested routes (e.g. /dashboard/support
 * inherits the dashboard's visible-help behaviour).
 */
export function isHelpVisibleOnPath(pathname: string): boolean {
  const path = pathname.toLowerCase();
  // The floating help button is now hidden globally, 
  // except for the Settings page per the user's request.
  if (path.startsWith('/dashboard/settings')) return true;
  return false;
}

/**
 * HelpAffordance is a fixed bottom-right help entry point mounted at
 * the App root so every page exposes a one-click route to support.
 *
 * Behaviour:
 *   - guest: clicking the button navigates to /contact
 *   - authed: clicking opens a small popover with three primary
 *     actions, then closes itself after the user picks one
 *
 * Visibility is controlled by isHelpVisibleOnPath; the widget
 * unmounts (no DOM at all) on routes where it would clash.
 *
 * Design tokens used here match the rest of the dashboard chrome:
 *   bg-brand           - primary action button
 *   bg-surface-elevated- popover surface
 *   border-border      - subtle dividers
 *   text-content       - default foreground
 *   text-content-muted - secondary copy
 * so the widget adopts both dark and light themes correctly without
 * per-component overrides.
 */
function HelpAffordance() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close popover on outside click. Mounted only while the popover is
  // open so we are not paying for a global mousedown listener on every
  // page.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (popoverRef.current?.contains(target)) return;
      if (buttonRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Close popover on Escape; complements the click-outside behaviour
  // and matches the rest of the dashboard's modal/popover conventions.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  // Close popover automatically when the route changes (e.g. when the
  // user clicks an action). Keeps the widget tidy without coupling
  // every action handler to a manual setOpen(false).
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const handleClick = useCallback(() => {
    if (!isAuthenticated) {
      navigate('/contact');
      return;
    }
    setOpen((prev) => !prev);
  }, [isAuthenticated, navigate]);

  const goNewTicket = useCallback(() => {
    navigate('/dashboard/support?new=1');
  }, [navigate]);

  const goMyTickets = useCallback(() => {
    navigate('/dashboard/support');
  }, [navigate]);

  const goCommunity = useCallback(() => {
    // Cross-route anchor: lands on the landing page and scrolls to
    // the #community section. The smart-anchor logic in
    // LandingFooter handles the in-page case symmetrically.
    navigate('/landing#community');
  }, [navigate]);

  const goFAQ = useCallback(() => {
    navigate('/faq');
  }, [navigate]);

  // Render nothing while auth is still resolving so the widget does
  // not flash a 'guest' state for an authenticated user on first paint.
  if (isLoading) return null;
  if (!isHelpVisibleOnPath(location.pathname)) return null;

  return (
    <div className="fixed bottom-6 right-6 z-overlay" aria-live="polite">
      {open && isAuthenticated && (
        <div
          ref={popoverRef}
          role="menu"
          aria-label="Help and support"
          className="absolute bottom-full right-0 mb-4 w-72 rounded-2xl border border-border
                     bg-black shadow-2xl overflow-hidden animate-fade-in ring-1 ring-white/5"
        >
          <header className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-1/50">
            <span className="text-[11px] font-black uppercase tracking-widest text-content-muted">
              Help & Support
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex items-center justify-center w-8 h-8 rounded-xl
                         text-content-muted hover:text-content hover:bg-surface-3
                         transition-all duration-fast focus-ring"
              aria-label="Close help menu"
            >
              <X size={16} />
            </button>
          </header>
          <div className="py-2">
            <ActionRow
              icon={<MessageSquarePlus size={16} />}
              label="Open a new ticket"
              description="Reach our support team"
              onClick={goNewTicket}
            />
            <ActionRow
              icon={<Inbox size={16} />}
              label="My tickets"
              description="View your history"
              onClick={goMyTickets}
            />
            <ActionRow
              icon={<BookOpen size={16} />}
              label="Browse FAQs"
              description="Self-serve answers"
              onClick={goFAQ}
            />
            <ActionRow
              icon={<Users size={16} />}
              label="Community channels"
              description="Facebook, Discord, Telegram"
              onClick={goCommunity}
            />
          </div>
        </div>
      )}
      <button
        ref={buttonRef}
        type="button"
        onClick={handleClick}
        aria-label={isAuthenticated ? 'Open help menu' : 'Contact support'}
        aria-expanded={open}
        className={`flex items-center justify-center w-12 h-12 rounded-2xl bg-white text-black
                   shadow-2xl hover:scale-105 active:scale-95 transition-all duration-fast focus-ring
                   ${open ? 'ring-2 ring-brand ring-offset-2 ring-offset-black' : ''}`}
        title={isAuthenticated ? 'Help & Support' : 'Contact us'}
      >
        <HelpCircle size={24} strokeWidth={2.5} />
      </button>
    </div>
  );
}

function ActionRow({
  icon,
  label,
  description,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className="w-full flex items-start gap-4 px-5 py-3.5 text-left
                 hover:bg-surface-2 transition-all duration-fast focus-ring group"
    >
      <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-brand/10 text-brand shrink-0 mt-0.5 group-hover:bg-brand/20 transition-colors">
        {icon}
      </span>
      <span className="flex flex-col min-w-0">
        <span className="text-[13px] font-black text-content tracking-tight">{label}</span>
        <span className="text-[11px] font-bold text-content-muted leading-tight mt-0.5">{description}</span>
      </span>
    </button>
  );
}

export default memo(HelpAffordance);
