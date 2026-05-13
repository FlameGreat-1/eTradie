import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import {
  DEFAULT_PASSWORD_POLICY,
  getPasswordPolicy,
  resetPassword,
  validateResetToken,
} from '../api/passwordReset';
import type { PasswordPolicy } from '../types';
import { toast } from '@/hooks/useToast';

type ValidationState = 'validating' | 'invalid' | 'valid' | 'disabled';

/**
 * ResetPasswordForm renders the second leg of the forgot-password flow.
 *
 * On mount it reads the `token` query parameter and probes the gateway
 * with the non-mutating /auth/password/reset/validate endpoint. The
 * server returns a uniform `{ valid: boolean }` shape and we render
 * one of three states based on it. The token itself is never inserted
 * into the DOM as a text node, only carried as a JSON body field on
 * the redemption POST.
 *
 * On success the gateway revokes all sessions, so we redirect to
 * /login with a one-time toast confirming the password change.
 */
export default function ResetPasswordForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = useMemo(
    () => (searchParams.get('token') || '').trim(),
    [searchParams],
  );

  const [state, setState] = useState<ValidationState>('validating');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [policy, setPolicy] = useState<PasswordPolicy>(DEFAULT_PASSWORD_POLICY);

  // Initial validation. Runs once on mount with the URL token. Fetches
  // the server-driven password policy in parallel via allSettled so a
  // policy-probe failure never blocks the token check (the form falls
  // back to DEFAULT_PASSWORD_POLICY in that case).
  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setState('invalid');
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      const [validation, policyResult] = await Promise.allSettled([
        validateResetToken({ token }),
        getPasswordPolicy(),
      ]);
      if (cancelled) return;
      if (
        policyResult.status === 'fulfilled' &&
        policyResult.value
      ) {
        setPolicy(policyResult.value);
        if (!policyResult.value.reset_enabled) {
          setState('disabled');
          return;
        }
      }
      if (validation.status === 'fulfilled') {
        setState(validation.value.valid ? 'valid' : 'invalid');
      } else {
        setState('invalid');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < policy.password_min_length) {
      setError(
        `Password must be at least ${policy.password_min_length} characters.`,
      );
      return;
    }
    if (password.length > policy.password_max_length) {
      setError(
        `Password must be at most ${policy.password_max_length} characters.`,
      );
      return;
    }
    if (password !== confirm) {
      setError('The two passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword({ token, new_password: password });
      toast({
        title: 'Password updated',
        description: 'You can now sign in with your new password.',
        variant: 'success',
      });
      navigate('/login', { replace: true });
    } catch (err: unknown) {
      let msg = 'Could not reset password. Please request a new link.';
      if (axios.isAxiosError(err) && err.response?.data?.error) {
        msg = err.response.data.error;
        if (err.response.status === 400) {
          // 400 from /reset includes the "link invalid/expired/used"
          // case. Flip to the invalid state so the user is offered
          // the "start over" path rather than a stuck form.
          setState('invalid');
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (state === 'validating') {
    return (
      <div className="w-full space-y-8">
        <div className="text-left">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: 'var(--landing-text)' }}
          >
            Verifying your link…
          </h1>
          <p
            className="text-sm opacity-50"
            style={{ color: 'var(--landing-text)' }}
          >
            One moment while we check your reset link.
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div
            className="h-8 w-8 rounded-full border-2 border-t-transparent animate-spin"
            style={{ borderColor: '#76B900', borderTopColor: 'transparent' }}
          />
        </div>
      </div>
    );
  }

  if (state === 'disabled') {
    return (
      <div className="w-full space-y-8">
        <div className="text-left">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: 'var(--landing-text)' }}
          >
            Password reset is temporarily unavailable
          </h1>
          <p
            className="text-sm opacity-60 leading-relaxed"
            style={{ color: 'var(--landing-text)' }}
          >
            We can't complete password resets at the moment. Please try
            again later or{' '}
            <Link
              to="/contact"
              className="underline decoration-[#76B900] decoration-2 underline-offset-4 font-bold"
              style={{ opacity: 1 }}
            >
              contact support
            </Link>
            .
          </p>
        </div>
        <div className="space-y-3">
          <Link
            to="/login"
            className="block w-full rounded-lg border px-4 py-3 text-sm font-medium text-center transition-all"
            style={{
              borderColor: 'var(--landing-card-border)',
              color: 'var(--landing-text)',
            }}
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  if (state === 'invalid') {
    return (
      <div className="w-full space-y-8">
        <div className="text-left">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: 'var(--landing-text)' }}
          >
            Reset link is invalid or expired
          </h1>
          <p
            className="text-sm opacity-60 leading-relaxed"
            style={{ color: 'var(--landing-text)' }}
          >
            This password reset link cannot be used. It may have
            expired, already been used, or been issued for a different
            account.
          </p>
        </div>

        <div className="space-y-3">
          <Link
            to="/forgot-password"
            className="block w-full rounded-lg bg-[#76B900] px-4 py-3.5 text-sm font-bold text-black
                       hover:bg-[#86cc00] transition-all text-center"
          >
            Request a new reset link
          </Link>
          <Link
            to="/login"
            className="block w-full rounded-lg border px-4 py-3 text-sm font-medium text-center transition-all"
            style={{
              borderColor: 'var(--landing-card-border)',
              color: 'var(--landing-text)',
            }}
          >
            Back to sign in
          </Link>
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
          Choose a new password
        </h1>
        <p
          className="text-sm opacity-50"
          style={{ color: 'var(--landing-text)' }}
        >
          Set a strong password you don't use anywhere else.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 px-4 py-3 text-sm text-danger animate-shake">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <label
              htmlFor="reset-password"
              className="block text-xs font-bold uppercase tracking-widest opacity-40"
              style={{ color: 'var(--landing-text)' }}
            >
              New password
            </label>
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="text-[10px] font-bold opacity-30 hover:opacity-100 transition-colors"
              style={{ color: 'var(--landing-text)' }}
            >
              {showPassword ? 'HIDE' : 'SHOW'}
            </button>
          </div>
          <input
            id="reset-password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={policy.password_min_length}
            maxLength={policy.password_max_length}
            autoComplete="new-password"
            className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
            style={{
              borderColor: 'var(--landing-card-border)',
              background: 'var(--landing-input-bg)',
              color: 'var(--landing-text)',
            }}
            placeholder={`At least ${policy.password_min_length} characters`}
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="reset-confirm"
            className="block text-xs font-bold uppercase tracking-widest opacity-40"
            style={{ color: 'var(--landing-text)' }}
          >
            Confirm new password
          </label>
          <input
            id="reset-confirm"
            type={showPassword ? 'text' : 'password'}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={policy.password_min_length}
            maxLength={policy.password_max_length}
            autoComplete="new-password"
            className="w-full rounded-lg border px-4 py-3 text-sm transition-all focus:outline-none"
            style={{
              borderColor: 'var(--landing-card-border)',
              background: 'var(--landing-input-bg)',
              color: 'var(--landing-text)',
            }}
            placeholder="Repeat your new password"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-[#76B900] px-4 py-3.5 text-sm font-bold text-black
                     hover:bg-[#86cc00] disabled:opacity-50 transition-all flex items-center justify-center gap-2 group"
        >
          {submitting ? (
            'Updating password…'
          ) : (
            <>
              Update password
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

      <p
        className="text-[11px] leading-relaxed opacity-50 text-center"
        style={{ color: 'var(--landing-text)' }}
      >
        After updating your password, every signed-in session for your
        account will be ended for security.
      </p>
    </div>
  );
}
