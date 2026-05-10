import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import DashboardLayout from '@/components/layout/DashboardLayout';
import AuthLayout from '@/components/layout/AuthLayout';

/* ─── Lazy-loaded pages ──────────────────────────────────── */
const LandingPage  = lazy(() => import('@/features/landing/LandingPage'));
const LoginPage    = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const OAuthCallbackPage = lazy(() => import('./pages/OAuthCallbackPage'));
const OAuthLinkCallbackPage = lazy(() => import('./pages/OAuthLinkCallbackPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AnalysisPage  = lazy(() => import('./pages/AnalysisPage'));
const TradesPage    = lazy(() => import('./pages/TradesPage'));
const JournalPage   = lazy(() => import('./pages/JournalPage'));
const SettingsPage  = lazy(() => import('./pages/SettingsPage'));
const SupportPage   = lazy(() => import('./pages/SupportPage'));

export function DashboardLoader() {
  return (
    <div className="flex items-center justify-center w-full h-full min-h-screen bg-app">
      <div className="flex flex-col items-center justify-center pointer-events-none gap-3">
        <img 
          src="/assets/sidebar/icons/logo.svg" 
          alt="Loading" 
          className="w-12 h-12"
          style={{ animation: 'logoZoom 1.2s ease-in-out infinite' }}
        />
        <style>{`
          @keyframes logoZoom {
            0%, 100% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.15); opacity: 1; }
          }
        `}</style>
      </div>
    </div>
  );
}

export function BlankLoader() {
  return <div className="min-h-screen bg-app" />;
}

function SmartSuspenseLoader() {
  if (window.location.pathname.startsWith('/dashboard')) {
    return <DashboardLoader />;
  }
  return <BlankLoader />;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <DashboardLoader />;
  if (!isAuthenticated) return <Navigate to="/landing" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const returnTo = searchParams.get('returnTo') || '/dashboard';

  if (isLoading) return <BlankLoader />;
  if (isAuthenticated) return <Navigate to={returnTo} replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <BlankLoader />;
  return <Navigate to={isAuthenticated ? '/dashboard' : '/landing'} replace />;
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<SmartSuspenseLoader />}>
      <Routes>
        {/* ── Public landing page ──────────────────────────── */}
        <Route
          path="/landing"
          element={
            <GuestRoute>
              <LandingPage />
            </GuestRoute>
          }
        />
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
          path="/auth/callback/google"
          element={
            <GuestRoute>
              <OAuthCallbackPage />
            </GuestRoute>
          }
        />
        <Route
          path="/dashboard/*"
          element={
            <ProtectedRoute>
              <DashboardLayout>
                <Suspense fallback={<DashboardLoader />}>
                  <Routes>
                    <Route index           element={<DashboardPage />} />
                    <Route path="analysis"  element={<AnalysisPage />} />
                    <Route path="trades"    element={<TradesPage />} />
                    <Route path="journal"   element={<JournalPage />} />
                    {/*
                      Authenticated Google-link callback. Must live
                      inside ProtectedRoute so the bearer token is
                      attached when the gateway resolves which user
                      the verified Google identity should bind to.
                      Declared before the catch-all settings/* route
                      so it wins the match.
                    */}
                    <Route
                      path="settings/oauth/callback/google"
                      element={<OAuthLinkCallbackPage />}
                    />
                    <Route path="settings/*" element={<SettingsPage />} />
                    <Route path="support"    element={<SupportPage />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Suspense>
              </DashboardLayout>
            </ProtectedRoute>
          }
        />
        {/* Redirect root to landing (guests) or dashboard (auth) */}
        <Route
          path="/"
          element={<RootRedirect />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
