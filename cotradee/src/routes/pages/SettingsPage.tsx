import { Routes, Route, NavLink } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Settings, Brain, Plug, Shield, User, CreditCard, Crown, Users, Cpu } from 'lucide-react';

import { useAuth, isAdmin } from '@/features/auth';

const ProfileSection = lazy(() => import('./settings/ProfileSection'));
const SymbolsSection = lazy(() => import('./settings/SymbolsSection'));
const LlmSection = lazy(() => import('./settings/LlmSection'));
const BrokerSection = lazy(() => import('./settings/BrokerSection'));
const ExecutionSection = lazy(() => import('./settings/ExecutionSection'));
const BillingSection = lazy(() => import('./settings/BillingSection'));
const PaymentSection = lazy(() => import('./settings/PaymentSection'));
const AdminUsersSection = lazy(() => import('./settings/AdminUsersSection'));
const AdminSystemAiSection = lazy(() => import('./settings/AdminSystemAiSection'));
export default function SettingsPage() {
  const { user } = useAuth();
  const admin = isAdmin(user);

  const links = [
    { to: '/dashboard/settings',           label: 'Profile',   icon: User,       end: true },
    { to: '/dashboard/settings/symbols',   label: 'Symbols',   icon: Settings },
    { to: '/dashboard/settings/llm',       label: 'API Key',   icon: Brain },
    { to: '/dashboard/settings/broker',    label: 'Broker',    icon: Plug },
    { to: '/dashboard/settings/execution', label: 'Execution', icon: Shield },
    { to: '/dashboard/settings/billing',   label: 'Billing',   icon: Crown },
    { to: '/dashboard/settings/payment',   label: 'Payment',   icon: CreditCard },
  ];

  if (admin) {
    links.push({ to: '/dashboard/settings/users',     label: 'Users',     icon: Users });
    links.push({ to: '/dashboard/settings/system-ai', label: 'System AI', icon: Cpu });
  }

  return (
    <div className="flex flex-col md:flex-row h-full animate-fade-in bg-white dark:bg-black">
      {/* Mobile: top tab strip */}
      <nav
        className="md:hidden flex items-center gap-2 px-4 py-3 border-b border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01]
                   overflow-x-auto no-scrollbar"
        aria-label="Settings"
      >
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-xl px-4 py-2 text-[10px] uppercase tracking-widest transition-all duration-300
               ${
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
        aria-label="Settings"
      >
        <h2 className="text-[10px] font-black text-black/30 dark:text-white/30 uppercase tracking-[0.2em] mb-6 ml-2">
          Settings
        </h2>
        <div className="space-y-1.5">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-[10px] uppercase tracking-widest transition-all duration-300
                 ${
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
            <Route index element={<ProfileSection />} />
            <Route path="profile" element={<ProfileSection />} />
            <Route path="symbols" element={<SymbolsSection />} />
            <Route path="llm" element={<LlmSection />} />
            <Route path="broker" element={<BrokerSection />} />
            <Route path="execution" element={<ExecutionSection />} />
            <Route path="billing" element={<BillingSection />} />
            <Route path="payment" element={<PaymentSection />} />
            {admin && (
              <>
                <Route path="users" element={<AdminUsersSection />} />
                <Route path="system-ai" element={<AdminSystemAiSection />} />
              </>
            )}
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}

