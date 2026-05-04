import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useGoogleOAuth } from '@/features/auth/hooks/useGoogleOAuth';
import { sanitiseReturnTo } from '@/features/auth/lib/oauthStorage';

/**
 * Landing page for the Google OAuth redirect when the user is
 * linking Google to an existing authenticated account.
 *
 * Distinct from OAuthCallbackPage:
 *   - lives inside the authenticated dashboard shell;
 *   - drives completeGoogleLink, which binds the verified Google
 *     identity to the current user and returns the updated profile;
 *   - on success returns the user to /settings (or the supplied
 *     return_to), not to the dashboard root.
 *
 * The completion call is guarded by a ref so React StrictMode's
 * double-mount in development cannot cause two POSTs against the
 * same single-use code.
 */
export default function OAuthLinkCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeGoogleLink } = useGoogleOAuth();
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
        const res = await completeGoogleLink({ code, state, error });
        // Default to /settings so the user lands back on the panel
        // they initiated the link from. sanitiseReturnTo enforces
        // same-origin and protects against open-redirect.
        const target = sanitiseReturnTo(res.return_to) || '/settings';
        navigate(target === '/' ? '/settings' : target, { replace: true });
      } catch (err: unknown) {
        const msg =
          err instanceof Error
            ? err.message
            : 'Could not finish Google account link';
        setErrorMessage(msg);
        setStatus('error');
      }
    })();
  }, [completeGoogleLink, navigate, searchParams]);

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
        <p className="text-sm text-content-muted">
          Linking your Google account…
        </p>
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
    <div className="w-full max-w-sm mx-auto space-y-4 py-10">
      <div className="text-center">
        <h1 className="text-xl font-bold text-content">Link failed</h1>
        <p className="text-sm text-content-muted mt-1">
          We couldn’t link your Google account.
        </p>
      </div>
      <div
        role="alert"
        className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger"
      >
        {errorMessage}
      </div>
      <Link
        to="/settings"
        replace
        className="block w-full text-center rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white
                   hover:bg-brand-dark transition-colors"
      >
        Back to settings
      </Link>
    </div>
  );
}
