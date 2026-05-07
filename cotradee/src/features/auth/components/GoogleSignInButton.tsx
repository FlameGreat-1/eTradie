import { useState } from 'react';
import { useGoogleOAuth } from '../hooks/useGoogleOAuth';

interface GoogleSignInButtonProps {
  /** Path the user should land on after a successful sign-in. */
  returnTo?: string;
  /** Visible label. "Sign in" on the login page, "Sign up" on register. */
  label?: string;
}

/**
 * Branded "Continue with Google" button.
 *
 * Visuals follow Google's identity guidelines: white background, dark
 * text, the official "G" mark on the left, and a 1px border that picks
 * up the surrounding theme. Behaviour is intentionally minimal: the
 * button delegates to useGoogleOAuth().startGoogleOAuth, which is
 * responsible for contacting the gateway, persisting state in
 * sessionStorage, and navigating the browser to Google's consent page.
 */
export default function GoogleSignInButton({
  returnTo,
  label = 'Continue with Google',
}: GoogleSignInButtonProps) {
  const { startGoogleOAuth, isStarting } = useGoogleOAuth();
  const [error, setError] = useState<string>('');

  const handleClick = async () => {
    setError('');
    try {
      await startGoogleOAuth(returnTo);
      // On success the page navigates to Google. If we get here, the
      // hook resolved without redirecting (e.g. blocked popup), which
      // we surface as an error.
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not start Google sign-in');
    }
  };

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isStarting}
        aria-busy={isStarting}
        aria-label={label}
        className="w-full inline-flex items-center justify-center gap-3 rounded-lg border px-4 py-3 text-sm font-bold transition-all"
        style={{
          borderColor: 'var(--landing-card-border)',
          background: 'var(--landing-btn-outline-bg)',
          color: 'var(--landing-text)'
        }}
      >
        <GoogleGlyph />
        <span>{isStarting ? 'Redirecting to Google…' : label}</span>
      </button>
      {error && (
        <div
          role="alert"
          className="rounded-lg bg-danger/10 border border-danger/20 px-3 py-2 text-xs text-danger"
        >
          {error}
        </div>
      )}
    </div>
  );
}

/**
 * Google's official multicoloured "G" mark, inlined as SVG so the
 * button has zero network dependency at first paint.
 */
function GoogleGlyph() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="#4285F4"
        d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.8745 2.6836-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.9087-2.2581c-.806.54-1.8368.8604-3.0473.8604-2.3445 0-4.3286-1.5832-5.0364-3.7104H.957v2.3318C2.4382 15.9831 5.4818 18 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.9636 10.7118A5.4106 5.4106 0 0 1 3.6818 9c0-.5932.1023-1.1700.2818-1.7118V4.9582H.957A8.9963 8.9963 0 0 0 0 9c0 1.4523.348 2.8264.957 4.0418l3.0066-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.5795c1.3214 0 2.5077.4541 3.4404 1.3459l2.5814-2.5814C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.957 4.9582l3.0066 2.33C4.6714 5.1627 6.6555 3.5795 9 3.5795z"
      />
    </svg>
  );
}
