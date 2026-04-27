import { Routes, Route, NavLink } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Settings, Brain, Plug, Shield, User } from 'lucide-react';

const ProfileSection = lazy(() => import('./settings/ProfileSection'));
const SymbolsSection = lazy(() => import('./settings/SymbolsSection'));
const LlmSection = lazy(() => import('./settings/LlmSection'));
const BrokerSection = lazy(() => import('./settings/BrokerSection'));
const ExecutionSection = lazy(() => import('./settings/ExecutionSection'));

const LINKS = [
  { to: '/settings',           label: 'Profile',   icon: User,     end: true },
  { to: '/settings/symbols',   label: 'Symbols',   icon: Settings },
  { to: '/settings/llm',       label: 'AI Engine', icon: Brain },
  { to: '/settings/broker',    label: 'Broker',    icon: Plug },
  { to: '/settings/execution', label: 'Execution', icon: Shield },
];

export default function SettingsPage() {
  return (
    <div className="flex flex-col md:flex-row h-full animate-fade-in">
      {/* Mobile: top tab strip */}
      <nav
        className="md:hidden flex items-center gap-1 px-2 py-2 border-b border-border bg-surface-1
                   overflow-x-auto no-scrollbar"
        aria-label="Settings"
      >
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors duration-fast focus-ring
               ${
                 isActive
                   ? 'bg-brand-soft text-brand'
                   : 'text-content-secondary hover:bg-surface-2'
               }`
            }
          >
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Desktop: vertical rail */}
      <nav
        className="hidden md:block w-56 flex-shrink-0 border-r border-border bg-surface-1 p-4"
        aria-label="Settings"
      >
        <h2 className="text-xs font-semibold text-content-muted uppercase tracking-wide mb-4">
          Settings
        </h2>
        <div className="space-y-1">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors duration-fast focus-ring
                 ${
                   isActive
                     ? 'bg-brand-soft text-brand'
                     : 'text-content-secondary hover:bg-surface-2'
                 }`
              }
            >
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 sm:p-6">
        <Suspense fallback={<div className="text-sm text-content-muted">Loading…</div>}>
          <Routes>
            <Route index element={<ProfileSection />} />
            <Route path="profile" element={<ProfileSection />} />
            <Route path="symbols" element={<SymbolsSection />} />
            <Route path="llm" element={<LlmSection />} />
            <Route path="broker" element={<BrokerSection />} />
            <Route path="execution" element={<ExecutionSection />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}
