import { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';

export default function RegisterForm() {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ username, email, password });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-5">
      <div className="text-center mb-8">
        <img src="/assets/sidebar/icons/logo.svg" alt="eTradie" className="w-12 h-12 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-content">Create Account</h1>
        <p className="text-sm text-content-muted mt-1">Start trading with AI intelligence</p>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="space-y-1.5">
        <label htmlFor="reg-username" className="block text-xs font-medium text-content-secondary">Username</label>
        <input id="reg-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)}
          required minLength={3} maxLength={32} autoComplete="username"
          className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content
                     placeholder:text-content-muted focus:border-brand focus:outline-none transition-colors"
          placeholder="Choose a username" />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="reg-email" className="block text-xs font-medium text-content-secondary">Email</label>
        <input id="reg-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          required autoComplete="email"
          className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content
                     placeholder:text-content-muted focus:border-brand focus:outline-none transition-colors"
          placeholder="you@example.com" />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="reg-password" className="block text-xs font-medium text-content-secondary">Password</label>
        <input id="reg-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
          required minLength={8} autoComplete="new-password"
          className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content
                     placeholder:text-content-muted focus:border-brand focus:outline-none transition-colors"
          placeholder="Min 8 characters" />
      </div>

      <button type="submit" disabled={loading}
        className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white
                   hover:bg-brand-dark disabled:opacity-50 transition-colors">
        {loading ? 'Creating…' : 'Create Account'}
      </button>
    </form>
  );
}
