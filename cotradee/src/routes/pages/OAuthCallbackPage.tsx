import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useGoogleOAuth } from '@/features/auth/hooks/useGoogleOAuth';
import { sanitiseReturnTo } from '@/features/auth/lib/oauthStorage';
import { DashboardLoader } from '@/routes';

/**
 * Landing page for the Google OAuth redirect.
 *
 * Google redirects the browser here with `?code=...&state=...` (or
 * `?error=...` on consent denial). This page:
 *   1. Parses the query parameters.
 *   2. Hands them to useGoogleOAuth().completeGoogleOAuth, which
 *      validates state, posts to the gateway, and hydrates the
 *      AuthContext via setTokens + fetchProfile.
 *   3. On success, navigates to the gateway-supplied return_to path
 *      (always same-origin and sanitised on both sides).
 *   4. On failure, renders a clear error panel with a back-to-login
 *      affordance. No silent redirects — the user always understands
 *      what happened.
 *
 * The completion call is guarded by a ref so React StrictMode's
 * double-mount in development cannot cause two POSTs against the same
 * single-use code.
 */
export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeGoogleOAuth } = useGoogleOAuth();
  const hasRun = useRef(false);

  const [status, setStatus] = useState<'pending' | 'error'>('pending');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const code = searchParams.get('code') ?? '';
    const state = searchParams.get('state') ?? '';
    const error = searchParams.get('error');

    void (async () => {
      try {
        const res = await completeGoogleOAuth({ code, state, error });
        const target = sanitiseReturnTo(res.return_to);
        navigate(target, { replace: true });
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Could not finish Google sign-in';
        setErrorMessage(msg);
        setStatus('error');
      }
    })();
  }, [completeGoogleOAuth, navigate, searchParams]);

  if (status === 'pending') {
    return <DashboardLoader />;
  }

  return (
    <div className="min-h-screen bg-app flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-5 bg-panel border border-panel p-8 rounded-2xl shadow-xl">
        <div className="text-center">
          <div className="w-12 h-12 bg-danger/10 text-danger rounded-full flex items-center justify-center mx-auto mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          </div>
          <h1 className="text-xl font-bold text-content">Sign-in failed</h1>
          <p className="text-sm text-content-muted mt-2">
            We couldn’t complete your Google sign-in.
          </p>
        </div>
        <div
          role="alert"
          className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger text-center"
        >
          {errorMessage}
        </div>
        <Link
          to="/login"
          replace
          className="block w-full text-center rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white
                     hover:bg-brand-dark transition-colors mt-2"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
