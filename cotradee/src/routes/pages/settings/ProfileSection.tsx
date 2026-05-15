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
    <div className="space-y-10 max-w-lg">
      <section>
        <div className="flex flex-col gap-0.5 mb-4">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Identity</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Account Information</h3>
        </div>
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-4 shadow-sm">
          <InfoRow label="Username" value={user?.username ?? '-'} />
          <InfoRow label="Email" value={user?.email ?? '-'} />
          <InfoRow label="Role" value={user?.role ?? '-'} />
          <InfoRow label="Tier" value={(user?.tier ?? 'free').replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())} />
          <InfoRow label="Status" value={user?.active ? 'Active' : 'Inactive'} />
        </div>
      </section>

      {env.googleOAuthEnabled && <ConnectedAccountsPanel />}

      <section>
        <div className="flex flex-col gap-0.5 mb-4">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Security</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Change Password</h3>
        </div>
        <form onSubmit={handlePasswordChange} className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm">
          {msg && (
            <div className={`rounded-xl px-4 py-3 text-[11px] font-bold tracking-tight leading-relaxed ${msg.includes('success') ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
              <span className="uppercase text-[9px] font-black tracking-widest bg-current/10 px-2 py-0.5 rounded-full mr-2">
                {msg.includes('success') ? 'Success' : 'Error'}
              </span>
              {msg}
            </div>
          )}
          <div className="space-y-2">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Current Password</label>
            <input type="password" autoComplete="current-password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} required
              className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
          </div>
          <div className="space-y-2">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">New Password</label>
            <input type="password" autoComplete="new-password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8}
              className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
          </div>
          <button type="submit" disabled={loading}
            className="rounded-xl bg-black dark:bg-white px-8 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40">
            {loading ? 'Updating…' : 'Update Password'}
          </button>
        </form>
      </section>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-[11px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">{label}</span>
      <span className="text-sm font-bold text-black dark:text-white tracking-tight">{value}</span>
    </div>
  );
}

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

  const isLinked =
    user?.auth_provider === 'google' ||
    user?.email_verified === true;

  const canDisconnect = isLinked && user?.auth_provider !== 'google';

  const handleConnect = async () => {
    setError('');
    setSuccess('');
    try {
      await startGoogleLink('/dashboard/settings');
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
      <div className="flex flex-col gap-0.5 mb-4">
        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Connections</div>
        <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Connected Accounts</h3>
      </div>
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm">
        {error && (
          <div role="alert" className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-[11px] font-bold text-red-500 tracking-tight">
            <span className="uppercase text-[9px] font-black tracking-widest bg-red-500/10 px-2 py-0.5 rounded-full mr-2">Error</span>
            {error}
          </div>
        )}
        {success && (
          <div role="status" className="rounded-xl border border-green-500/20 bg-green-500/5 p-4 text-[11px] font-bold text-green-500 tracking-tight">
            <span className="uppercase text-[9px] font-black tracking-widest bg-green-500/10 px-2 py-0.5 rounded-full mr-2">Success</span>
            {success}
          </div>
        )}

        <div className="flex items-center gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-white/5 flex items-center justify-center shadow-sm">
            <GoogleGlyph />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-black dark:text-white tracking-tight">Google</div>
            <div className="text-[11px] font-medium text-black/40 dark:text-white/40 truncate mt-0.5">
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
                className="rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-20"
              >
                {isLinking ? 'Redirecting…' : 'Connect'}
              </button>
            )}
            {isLinked && canDisconnect && !confirmingDisconnect && (
              <button
                type="button"
                onClick={() => setConfirmingDisconnect(true)}
                className="rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-all"
              >
                Disconnect
              </button>
            )}
            {isLinked && !canDisconnect && (
              <span className="inline-flex items-center rounded-full bg-green-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-green-600 dark:text-green-400 border border-green-500/20">
                Linked
              </span>
            )}
          </div>
        </div>

        {confirmingDisconnect && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 space-y-4 animate-in fade-in slide-in-from-top-2">
            <p className="text-xs font-bold text-red-500/80 leading-relaxed">
              Disconnect Google? You’ll need to sign in with your
              username and password afterwards.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isUnlinking}
                className="rounded-lg bg-red-500 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white hover:bg-red-600 transition-all disabled:opacity-50 shadow-lg shadow-red-500/10"
              >
                {isUnlinking ? 'Disconnecting…' : 'Yes, disconnect'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDisconnect(false)}
                disabled={isUnlinking}
                className="rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-all"
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
