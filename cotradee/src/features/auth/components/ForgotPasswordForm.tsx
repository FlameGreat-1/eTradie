import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { requestPasswordReset } from '../api/passwordReset';

/**
 * ForgotPasswordForm collects an email address and triggers a reset.
 *
 * The gateway intentionally returns the same generic 202 envelope for
 * every outcome (account exists, account is federated, account is
 * deactivated, throttled) so this form deliberately shows a single
 * success state for all of them. The user is told to check their inbox
 * AND junk folder; if no email arrives, they should retry.
 */
export default function ForgotPasswordForm() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    setLoading(true);
    try {
      await requestPasswordReset({ email: trimmed });
      setSubmitted(true);
    } catch (err: unknown) {
      let msg = 'Could not send the reset email. Please try again.';
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

  if (submitted) {
    return (
      <div className="w-full space-y-8">
        <div className="text-left">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: 'var(--landing-text)' }}
          >
            Check your inbox
          </h1>
          <p
            className="text-sm opacity-60 leading-relaxed"
            style={{ color: 'var(--landing-text)' }}
          >
            If an account exists for{' '}
            <span className="font-semibold" style={{ opacity: 1 }}>
              {email.trim()}
            </span>
            , we just sent a password reset link to it. The link will
            expire in 60 minutes and can be used only once.
          </p>
          <p
            className="text-sm opacity-50 mt-4 leading-relaxed"
            style={{ color: 'var(--landing-text)' }}
          >
            Don't see it? Check your spam or junk folder. You can also{' '}
            <button
              type="button"
              onClick={() => {
                setSubmitted(false);
                setEmail('');
              }}
              className="underline decoration-[#76B900] decoration-2 underline-offset-4 font-bold"
              style={{ color: 'var(--landing-text)', opacity: 1 }}
            >
              try a different email
            </button>
            .
          </p>
        </div>

        <div className="flex items-center gap-3 py-2">
          <div
            className="flex-1 h-px opacity-10"
            style={{ background: 'var(--landing-text)' }}
          />
          <p
            className="text-xs font-medium opacity-60"
            style={{ color: 'var(--landing-text)' }}
          >
            Remembered your password?{' '}
            <Link
              to="/login"
              className="opacity-100 underline decoration-[#76B900] decoration-2 underline-offset-4 font-bold"
            >
              Sign in
            </Link>
          </p>
          <div
            className="flex-1 h-px opacity-10"
            style={{ background: 'var(--landing-text)' }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-8">
      <div className="text-left">
        <h1
          className="text-3xl font-bold mb-2"
          style={{ color: 'var(--landing-text)' }}
        >
          Forgot your password?
        </h1>
        <p
          className="text-sm opacity-50"
          style={{ color: 'var(--landing-text)' }}
        >
          Enter the email address associated with your account and we'll
          email you a link to reset it.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger animate-shake">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label
            htmlFor="forgot-email"
            className="block text-xs font-bold uppercase tracking-widest opacity-40"
            style={{ color: 'var(--landing-text)' }}
          >
            Email
          </label>
          <input
            id="forgot-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
            style={{
              borderColor: 'var(--landing-card-border)',
              background: 'var(--landing-input-bg)',
              color: 'var(--landing-text)',
            }}
            placeholder="you@domain.com"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[#76B900] px-4 py-3.5 text-sm font-bold text-black
                     hover:bg-[#86cc00] disabled:opacity-50 transition-all flex items-center justify-center gap-2 group"
        >
          {loading ? (
            'Sending reset link…'
          ) : (
            <>
              Send reset link
              <svg
                className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </>
          )}
        </button>
      </form>

      <div className="flex items-center gap-3 py-2">
        <div
          className="flex-1 h-px opacity-10"
          style={{ background: 'var(--landing-text)' }}
        />
        <p
          className="text-xs font-medium opacity-60"
          style={{ color: 'var(--landing-text)' }}
        >
          Remembered your password?{' '}
          <Link
            to="/login"
            className="opacity-100 underline decoration-[#76B900] decoration-2 underline-offset-4 font-bold"
          >
            Sign in
          </Link>
        </p>
        <div
          className="flex-1 h-px opacity-10"
          style={{ background: 'var(--landing-text)' }}
        />
      </div>
    </div>
  );
}
