import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import DashboardLayout from '@/components/layout/DashboardLayout';
import AuthLayout from '@/components/layout/AuthLayout';
import { ChunkErrorBoundary } from './ChunkErrorBoundary';

/* ─── Lazy-loaded pages ──────────────────────────────────── */
const LandingPage  = lazy(() => import('@/features/landing/LandingPage'));
const PricingPage  = lazy(() => import('./pages/PricingPage'));
const ProcessPage  = lazy(() => import('./pages/ProcessPage'));
const LoginPage    = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const ResetPasswordPage  = lazy(() => import('./pages/ResetPasswordPage'));
const OAuthCallbackPage = lazy(() => import('./pages/OAuthCallbackPage'));
const OAuthLinkCallbackPage = lazy(() => import('./pages/OAuthLinkCallbackPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AnalysisPage  = lazy(() => import('./pages/AnalysisPage'));
const TradesPage    = lazy(() => import('./pages/TradesPage'));
const JournalPage   = lazy(() => import('./pages/JournalPage'));
const TradingSystemPage = lazy(() => import('./pages/TradingSystemPage'));
const PerformancePage = lazy(() => import('./pages/PerformancePage'));
const SetupPage = lazy(() => import('./pages/SetupPage'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
const SettingsPage  = lazy(() => import('./pages/SettingsPage'));
const SupportPage   = lazy(() => import('./pages/SupportPage'));
const CommunityPage = lazy(() => import('./pages/CommunityPage'));

/* ─── Legal & compliance pages (public, reachable by guests and authed users) ─── */
const TermsPage           = lazy(() => import('./pages/TermsPage'));
const PrivacyPage         = lazy(() => import('./pages/PrivacyPage'));
const RiskDisclosurePage  = lazy(() => import('./pages/RiskDisclosurePage'));
const RefundPage          = lazy(() => import('./pages/RefundPage'));
const BillingPolicyPage   = lazy(() => import('./pages/BillingPolicyPage'));
const CookiePolicyPage    = lazy(() => import('./pages/CookiePolicyPage'));
const ComplaintsPage      = lazy(() => import('./pages/ComplaintsPage'));
const ContactPage          = lazy(() => import('./pages/ContactPage'));
const FAQPage              = lazy(() => import('@/features/faq/FAQPage'));

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

// Route guards read the explicit auth `status` (see AuthContext) rather
// than combining isLoading + isAuthenticated. Each guard's three cases
// are spelled out so the intent is unambiguous to the next reader.

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  // An authenticated surface genuinely needs to know WHO the user is
  // before it can render protected data, so it is the only place that
  // shows a loader while the probe is in flight.
  if (status === 'loading') return <DashboardLoader />;
  if (status === 'guest') {
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?returnTo=${returnTo}`} replace />;
  }
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const returnTo = searchParams.get('returnTo') || '/dashboard';

  // Public surface: render content for BOTH 'loading' and 'guest'. These
  // pages (landing, pricing, login, ...) never depend on auth state to
  // display, so they must paint instantly even when the backend is slow
  // or undeployed — no spinner, no blank. Only a resolved authenticated
  // session redirects a returning user on to their destination.
  if (status === 'authenticated') return <Navigate to={returnTo} replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { status } = useAuth();
  // "/" renders the public landing page DIRECTLY for 'loading' and
  // 'guest' (single hop — no redirect-to-a-redirect, no blank loader).
  // The landing page is the same component served at /landing. Only a
  // resolved authenticated session navigates to the dashboard.
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />;
  return (
    <GuestRoute>
      <LandingPage />
    </GuestRoute>
  );
}

export default function AppRoutes() {
  return (
    <ChunkErrorBoundary fallback={<SmartSuspenseLoader />}>
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
          path="/pricing"
          element={
            <GuestRoute>
              <PricingPage />
            </GuestRoute>
          }
        />
        <Route
          path="/process"
          element={
            <GuestRoute>
              <ProcessPage />
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
        {/* ── Forgot / reset password (public, guest-only) ──────────
            Both pages live under GuestRoute so an already-authenticated
            user is bounced to /dashboard; a signed-in user who wants to
            change their password uses Settings → Profile, not this
            flow. AuthLayout reuses the marketing-side chrome so the
            visual language matches /login and /register. */}
        <Route
          path="/forgot-password"
          element={
            <GuestRoute>
              <AuthLayout><ForgotPasswordPage /></AuthLayout>
            </GuestRoute>
          }
        />
        <Route
          path="/reset-password"
          element={
            <GuestRoute>
              <AuthLayout><ResetPasswordPage /></AuthLayout>
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
        {/* ── Public legal & compliance pages ─────────────────
            Wrapped in neither GuestRoute nor ProtectedRoute so they
            are reachable from anywhere (marketing site, authed app,
            external emails, Paddle compliance review). */}
        <Route path="/terms"            element={<TermsPage />} />
        <Route path="/privacy"          element={<PrivacyPage />} />
        <Route path="/risk-disclosure"  element={<RiskDisclosurePage />} />
        <Route path="/refund"           element={<RefundPage />} />
        <Route path="/billing-policy"   element={<BillingPolicyPage />} />
        <Route path="/cookie"           element={<CookiePolicyPage />} />
        <Route path="/complaints"       element={<ComplaintsPage />} />
        <Route path="/contact"          element={<ContactPage />} />
        {/*
          /faq is the canonical public FAQ surface. /faqs is the
          plural-vs-singular alias so a URL slip (or a tweet linking
          /faqs#thing) never produces a 404. SEO best practice is to
          serve one canonical and 301 the other; the SPA approximates
          this with a client-side Navigate(replace).
        */}
        <Route path="/faq"              element={<FAQPage />} />
        <Route path="/faqs"             element={<Navigate to="/faq" replace />} />
        {/* ── Onboarding wizard (protected, outside DashboardLayout) ── */}
        <Route
          path="/onboarding"
          element={
            <ProtectedRoute>
              <Suspense fallback={<DashboardLoader />}>
                <OnboardingPage />
              </Suspense>
            </ProtectedRoute>
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
                    <Route path="analysis"        element={<AnalysisPage />} />
                    <Route path="trades"          element={<TradesPage />} />
                    <Route path="journal"         element={<JournalPage />} />
                    <Route path="trading-system"  element={<TradingSystemPage />} />
                    <Route path="trading-plan"    element={<TradingSystemPage />} />
                    <Route path="performance"     element={<PerformancePage />} />
                    <Route path="setup"           element={<SetupPage />} />
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
                    <Route path="community"  element={<CommunityPage />} />
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
    </ChunkErrorBoundary>
  );
}
