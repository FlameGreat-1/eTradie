import { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import GoogleSignInButton from './GoogleSignInButton';
import SocialAuthDivider from './SocialAuthDivider';
import { env } from '@/config/env';

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
      let msg = 'Registration failed';
      if (axios.isAxiosError(err) && err.response?.data?.error) {
        msg = err.response.data.error;
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full space-y-8">
      <div className="text-left">
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--landing-text)' }}>Join Exoper</h1>
        <p className="text-sm opacity-50" style={{ color: 'var(--landing-text)' }}>Create your institutional trading account.</p>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger animate-shake">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {env.googleOAuthEnabled && (
          <div className="space-y-4">
            <GoogleSignInButton label="Sign up with Google" />
            <SocialAuthDivider label="or register with email" />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="reg-username" className="block text-xs font-bold uppercase tracking-widest opacity-40" style={{ color: 'var(--landing-text)' }}>
              Username
            </label>
            <input
              id="reg-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={32}
              autoComplete="username"
              className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
              style={{ 
                borderColor: 'var(--landing-card-border)', 
                background: 'var(--landing-input-bg)',
                color: 'var(--landing-text)'
              }}
              placeholder="trader_pro"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="reg-email" className="block text-xs font-bold uppercase tracking-widest opacity-40" style={{ color: 'var(--landing-text)' }}>
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
              style={{ 
                borderColor: 'var(--landing-card-border)', 
                background: 'var(--landing-input-bg)',
                color: 'var(--landing-text)'
              }}
              placeholder="you@domain.com"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="reg-password" className="block text-xs font-bold uppercase tracking-widest opacity-40" style={{ color: 'var(--landing-text)' }}>
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
              style={{ 
                borderColor: 'var(--landing-card-border)', 
                background: 'var(--landing-input-bg)',
                color: 'var(--landing-text)'
              }}
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#76B900] px-4 py-3.5 text-sm font-bold text-black
                       hover:bg-[#86cc00] disabled:opacity-50 transition-all flex items-center justify-center gap-2 group"
          >
            {loading ? 'Creating account…' : (
              <>
                Create Account
                <svg className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                  <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
              </>
            )}
          </button>
        </form>
      </div>

      <div className="flex items-center gap-3 py-2">
        <div className="flex-1 h-px opacity-10" style={{ background: 'var(--landing-text)' }} />
        <p className="text-xs font-medium opacity-60" style={{ color: 'var(--landing-text)' }}>
          Already have an account? <a href="/login" className="opacity-100 underline decoration-[#76B900] decoration-2 underline-offset-4 font-bold">Sign in</a>
        </p>
        <div className="flex-1 h-px opacity-10" style={{ background: 'var(--landing-text)' }} />
      </div>
    </div>
  );
}
