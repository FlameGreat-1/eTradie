import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Crown, Receipt, Activity, ShieldCheck } from 'lucide-react';
import { useAuth, isAdmin } from '@/features/auth';

const AdminSubscriptionsSection = lazy(() => import('./AdminSubscriptionsSection'));
const AdminTransactionsSection = lazy(() => import('./AdminTransactionsSection'));
const AdminLLMUsageSection = lazy(() => import('./AdminLLMUsageSection'));

const LINKS = [
  { to: '/dashboard/admin',              label: 'Subscriptions', icon: Crown,    end: true },
  { to: '/dashboard/admin/transactions', label: 'Transactions',  icon: Receipt },
  { to: '/dashboard/admin/llm-usage',    label: 'AI Tokens',     icon: Activity },
];

export default function AdminPage() {
  const { user } = useAuth();

  // Defence-in-depth: the route is already gated by AdminRoute, but
  // if a non-admin somehow renders this component (dev tools, a stale
  // bundle), we short-circuit to the dashboard. Backend RequireAdmin
  // is the actual source of truth; this is purely a UX guard.
  if (!isAdmin(user)) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex flex-col md:flex-row h-full animate-fade-in bg-white dark:bg-black">
      {/* Mobile: top tab strip */}
      <nav
        className="md:hidden flex items-center gap-2 px-4 py-3 border-b border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01] overflow-x-auto no-scrollbar"
        aria-label="Admin"
      >
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-xl px-4 py-2 text-[10px] uppercase tracking-widest transition-all duration-300 ${
                isActive
                  ? 'bg-black dark:bg-white text-white dark:text-black font-black shadow-lg shadow-black/10 dark:shadow-white/10'
                  : 'text-black/40 dark:text-white/40 font-bold hover:bg-black/5 dark:hover:bg-white/5'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={12} strokeWidth={isActive ? 3 : 2} className="transition-all" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Desktop: vertical rail */}
      <nav
        className="hidden md:block w-64 flex-shrink-0 border-r border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01] p-6"
        aria-label="Admin"
      >
        <div className="flex items-center gap-2 mb-6 ml-2">
          <ShieldCheck size={14} className="text-success" strokeWidth={2.5} />
          <h2 className="text-[10px] font-black text-black/30 dark:text-white/30 uppercase tracking-[0.2em]">
            Admin
          </h2>
        </div>
        <div className="space-y-1.5">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-[10px] uppercase tracking-widest transition-all duration-300 ${
                  isActive
                    ? 'bg-black dark:bg-white text-white dark:text-black font-black shadow-lg shadow-black/10 dark:shadow-white/10 translate-x-1'
                    : 'text-black/40 dark:text-white/40 font-bold hover:bg-black/5 dark:hover:bg-white/5 hover:translate-x-1'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={14} strokeWidth={isActive ? 3 : 2} className="transition-all" />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-white dark:bg-black p-6 lg:p-10">
        <Suspense fallback={<div className="text-sm text-content-muted">Loading…</div>}>
          <Routes>
            <Route index element={<AdminSubscriptionsSection />} />
            <Route path="transactions" element={<AdminTransactionsSection />} />
            <Route path="llm-usage" element={<AdminLLMUsageSection />} />
            <Route path="*" element={<Navigate to="/dashboard/admin" replace />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}
