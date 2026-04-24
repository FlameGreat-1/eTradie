import { useState, type FormEvent } from 'react';
import { useAuth } from '@/features/auth';
import { changePassword } from '@/features/auth/api/profile';

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
