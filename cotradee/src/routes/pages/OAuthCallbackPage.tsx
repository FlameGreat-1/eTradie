import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useGoogleOAuth } from '@/features/auth/hooks/useGoogleOAuth';
import { sanitiseReturnTo } from '@/features/auth/lib/oauthStorage';

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
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex flex-col items-center justify-center gap-4 py-10"
      >
        <img
          src="/assets/sidebar/icons/logo.svg"
          alt=""
          aria-hidden="true"
          className="w-10 h-10"
          style={{ animation: 'logoZoom 1.2s ease-in-out infinite' }}
        />
        <p className="text-sm text-content-muted">Finishing Google sign-in…</p>
        <style>{`
          @keyframes logoZoom {
            0%, 100% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.15); opacity: 1; }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm space-y-4">
      <div className="text-center">
        <h1 className="text-xl font-bold text-content">Sign-in failed</h1>
        <p className="text-sm text-content-muted mt-1">
          We couldn’t complete your Google sign-in.
        </p>
      </div>
      <div
        role="alert"
        className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger"
      >
        {errorMessage}
      </div>
      <Link
        to="/login"
        replace
        className="block w-full text-center rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white
                   hover:bg-brand-dark transition-colors"
      >
        Back to sign in
      </Link>
    </div>
  );
}
