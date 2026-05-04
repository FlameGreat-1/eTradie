import { useState, type FormEvent } from 'react';
import { useAuth, useGoogleOAuth } from '@/features/auth';
import { changePassword } from '@/features/auth/api/profile';
import { env } from '@/config/env';

export default function ProfileSection() {
  const { user } = useAuth();
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setMsg('');
    setLoading(true);
    try {
      await changePassword({ current_password: currentPw, new_password: newPw });
      setMsg('Password updated successfully');
      setCurrentPw('');
      setNewPw('');
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-lg">
      <section>
        <h3 className="text-sm font-semibold text-content mb-4">Account Information</h3>
        <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-3">
          <InfoRow label="Username" value={user?.username ?? '-'} />
          <InfoRow label="Email" value={user?.email ?? '-'} />
          <InfoRow label="Role" value={user?.role ?? '-'} />
          <InfoRow label="Status" value={user?.active ? 'Active' : 'Inactive'} />
        </div>
      </section>

      {env.googleOAuthEnabled && <ConnectedAccountsPanel />}

      <section>
        <h3 className="text-sm font-semibold text-content mb-4">Change Password</h3>
        <form onSubmit={handlePasswordChange} className="rounded-xl border border-border bg-surface-1 p-5 space-y-4">
          {msg && (
            <div className={`rounded-lg px-3 py-2 text-xs ${msg.includes('success') ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
              {msg}
            </div>
          )}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-content-secondary">Current Password</label>
            <input type="password" autoComplete="current-password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} required
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-content
                         focus:border-brand focus:outline-none transition-colors" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-content-secondary">New Password</label>
            <input type="password" autoComplete="new-password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8}
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-content
                         focus:border-brand focus:outline-none transition-colors" />
          </div>
          <button type="submit" disabled={loading}
            className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white hover:bg-brand-dark disabled:opacity-50 transition-colors">
            {loading ? 'Updating…' : 'Update Password'}
          </button>
        </form>
      </section>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-content-muted">{label}</span>
      <span className="text-xs font-medium text-content">{value}</span>
    </div>
  );
}

/**
 * Connected accounts panel.
 *
 * Surfaces the Google identity binding for the current user and is
 * the dashboard counterpart to the gateway's
 *   "please sign in with your password and link Google from settings"
 * error. Renders one of three states:
 *
 *   - Not linked        → "Connect Google account" button.
 *   - Linked (local)    → status + "Disconnect" button.
 *   - Linked (google)   → status only; disconnecting a Google-only
 *                         account would leave it with no credential.
 *
 * The disconnect action is gated by an inline confirmation prompt.
 */
function ConnectedAccountsPanel() {
  const { user } = useAuth();
  const {
    startGoogleLink,
    unlinkGoogle,
    isLinking,
    isUnlinking,
  } = useGoogleOAuth();

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);

  // Treat the user as linked when their auth_provider is 'google'
  // OR the gateway has flagged the email as identity-provider
  // verified. Older gateway builds may omit auth_provider, so the
  // email_verified fallback keeps the UI useful in that window.
  const isLinked =
    user?.auth_provider === 'google' ||
    user?.email_verified === true;

  // A user whose only credential is Google must not be allowed to
  // unlink, because doing so would leave them with no way to sign in.
  // They need to set a local password first (separate flow).
  const canDisconnect = isLinked && user?.auth_provider !== 'google';

  const handleConnect = async () => {
    setError('');
    setSuccess('');
    try {
      await startGoogleLink('/settings');
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not start Google account link',
      );
    }
  };

  const handleDisconnect = async () => {
    setError('');
    setSuccess('');
    try {
      await unlinkGoogle();
      setSuccess('Google account disconnected');
      setConfirmingDisconnect(false);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not disconnect Google account',
      );
    }
  };

  return (
    <section>
      <h3 className="text-sm font-semibold text-content mb-4">
        Connected accounts
      </h3>
      <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-4">
        {error && (
          <div
            role="alert"
            className="rounded-lg bg-danger/10 border border-danger/20 px-3 py-2 text-xs text-danger"
          >
            {error}
          </div>
        )}
        {success && (
          <div
            role="status"
            className="rounded-lg bg-success/10 border border-success/20 px-3 py-2 text-xs text-success"
          >
            {success}
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg border border-border bg-white flex items-center justify-center">
            <GoogleGlyph />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-content">Google</div>
            <div className="text-xs text-content-muted truncate">
              {isLinked
                ? `Connected · ${user?.email ?? ''}`
                : 'Sign in faster by connecting your Google account.'}
            </div>
          </div>
          <div className="flex-shrink-0">
            {!isLinked && (
              <button
                type="button"
                onClick={handleConnect}
                disabled={isLinking}
                aria-busy={isLinking}
                className="rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white
                           hover:bg-brand-dark disabled:opacity-60 disabled:cursor-not-allowed
                           transition-colors"
              >
                {isLinking ? 'Redirecting…' : 'Connect'}
              </button>
            )}
            {isLinked && canDisconnect && !confirmingDisconnect && (
              <button
                type="button"
                onClick={() => setConfirmingDisconnect(true)}
                className="rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-semibold text-content
                           hover:bg-surface-3 transition-colors"
              >
                Disconnect
              </button>
            )}
            {isLinked && !canDisconnect && (
              <span className="inline-flex items-center rounded-lg bg-success/10 px-2.5 py-1 text-[11px] font-semibold text-success">
                Linked
              </span>
            )}
          </div>
        </div>

        {confirmingDisconnect && (
          <div className="rounded-lg border border-border bg-surface-2 p-3 space-y-2">
            <p className="text-xs text-content">
              Disconnect Google? You’ll need to sign in with your
              username and password afterwards.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isUnlinking}
                aria-busy={isUnlinking}
                className="rounded-lg bg-danger px-3 py-1.5 text-xs font-semibold text-white
                           hover:bg-danger/90 disabled:opacity-60 disabled:cursor-not-allowed
                           transition-colors"
              >
                {isUnlinking ? 'Disconnecting…' : 'Yes, disconnect'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDisconnect(false)}
                disabled={isUnlinking}
                className="rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-xs font-semibold text-content
                           hover:bg-surface-2 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

/** Inline Google "G" mark used in the connected-accounts row. */
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
