import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import DashboardLayout from '@/components/layout/DashboardLayout';
import AuthLayout from '@/components/layout/AuthLayout';

/* ─── Lazy-loaded pages ──────────────────────────────────── */
const LoginPage    = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AnalysisPage  = lazy(() => import('./pages/AnalysisPage'));
const TradesPage    = lazy(() => import('./pages/TradesPage'));
const JournalPage   = lazy(() => import('./pages/JournalPage'));
const SettingsPage  = lazy(() => import('./pages/SettingsPage'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full bg-app">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-brand border-t-transparent animate-spin" />
        <span className="text-xs text-content-muted uppercase tracking-wider">
          Loading
        </span>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <AuthLayout><LoginPage /></AuthLayout>
            </GuestRoute>
          }
        />
        <Route
          path="/register"
          element={
            <GuestRoute>
              <AuthLayout><RegisterPage /></AuthLayout>
            </GuestRoute>
          }
        />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <DashboardLayout>
                <Suspense fallback={<PageLoader />}>
                  <Routes>
                    <Route index           element={<DashboardPage />} />
                    <Route path="analysis"  element={<AnalysisPage />} />
                    <Route path="trades"    element={<TradesPage />} />
                    <Route path="journal"   element={<JournalPage />} />
                    <Route path="settings/*" element={<SettingsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </DashboardLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}
