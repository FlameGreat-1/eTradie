import { Routes, Route, NavLink } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Settings, Brain, Plug, Shield, User } from 'lucide-react';

const ProfileSection = lazy(() => import('./settings/ProfileSection'));
const SymbolsSection = lazy(() => import('./settings/SymbolsSection'));
const LlmSection = lazy(() => import('./settings/LlmSection'));
const BrokerSection = lazy(() => import('./settings/BrokerSection'));
const ExecutionSection = lazy(() => import('./settings/ExecutionSection'));

const links = [
  { to: '/settings', label: 'Profile', icon: User, end: true },
  { to: '/settings/symbols', label: 'Symbols', icon: Settings },
  { to: '/settings/llm', label: 'AI Engine', icon: Brain },
  { to: '/settings/broker', label: 'Broker', icon: Plug },
  { to: '/settings/execution', label: 'Execution', icon: Shield },
];

export default function SettingsPage() {
  return (
    <div className="flex h-full animate-fade-in">
      {/* Sidebar navigation */}
      <nav className="w-56 flex-shrink-0 border-r border-border bg-surface-1 p-4">
        <h2 className="text-xs font-semibold text-content-muted uppercase tracking-wide mb-4">Settings</h2>
        <div className="space-y-1">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-brand/10 text-brand'
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
      <div className="flex-1 overflow-auto p-6">
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
