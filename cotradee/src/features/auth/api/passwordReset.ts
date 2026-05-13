import { api } from '@/lib/axios';
import type {
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  PasswordPolicy,
  ValidateResetTokenRequest,
  ValidateResetTokenResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
} from '../types';

/**
 * DEFAULT_PASSWORD_POLICY is the compile-time fallback used when the
 * gateway's /auth/password/policy endpoint cannot be reached. The
 * numbers mirror the backend defaults (auth/models.go PasswordMinLength
 * /MaxLength and AUTH_PASSWORD_RESET_TOKEN_TTL_SECONDS=3600); they are
 * SAFE to use because the backend will re-validate every input on
 * submit anyway. The defaults exist purely so the form can render a
 * sensible placeholder while the policy probe is in flight, and so a
 * transient probe failure does not block the user from trying.
 */
export const DEFAULT_PASSWORD_POLICY: PasswordPolicy = {
  reset_enabled: true,
  token_expires_minutes: 60,
  password_min_length: 8,
  password_max_length: 72,
};

/**
 * Trigger a password-reset email.
 *
 * The gateway always returns 202 with a generic envelope regardless of
 * whether an account exists for the supplied email. The caller MUST
 * NOT branch on the response to infer account state; doing so would
 * re-introduce the user-enumeration leak the backend explicitly
 * defends against.
 *
 * Network failures and 4xx-input errors still throw, so the form can
 * surface them to the user. The backend reserves 400 for malformed
 * input (missing/invalid email), 429 for rate-limit, and 503 when the
 * feature is not configured on the deployment.
 */
export async function requestPasswordReset(
  payload: ForgotPasswordRequest,
): Promise<ForgotPasswordResponse> {
  const { data } = await api.gateway.post<ForgotPasswordResponse>(
    '/auth/password/forgot',
    payload,
  );
  return data;
}

/**
 * Non-mutating probe of a reset token. Lets the SPA decide whether to
 * render the password form or a 'link expired' message without burning
 * the token. The gateway returns the same `{ valid: boolean }` shape
 * regardless of WHY the token is unusable (expired vs consumed vs
 * not-found vs deactivated user vs federated user) so the SPA cannot
 * be used as an oracle.
 */
export async function validateResetToken(
  payload: ValidateResetTokenRequest,
): Promise<ValidateResetTokenResponse> {
  const { data } = await api.gateway.post<ValidateResetTokenResponse>(
    '/auth/password/reset/validate',
    payload,
  );
  return data;
}

/**
 * Redeem the reset token and set a new password. Single-use: a second
 * call with the same token returns 400. On success the gateway revokes
 * every session for the user and clears the cookie jar on the response,
 * so the SPA should route the user to /login to authenticate fresh.
 */
export async function resetPassword(
  payload: ResetPasswordRequest,
): Promise<ResetPasswordResponse> {
  const { data } = await api.gateway.post<ResetPasswordResponse>(
    '/auth/password/reset',
    payload,
  );
  return data;
}

/**
 * Fetch the server-driven password policy: TTL of the reset token in
 * minutes, password length bounds, and a feature-enabled flag. Public
 * GET; never throws — returns DEFAULT_PASSWORD_POLICY on any transport
 * or shape failure so the UI never blocks on this call. The caller
 * should treat the return value as advisory and rely on the gateway
 * to re-validate on submit.
 */
export async function getPasswordPolicy(): Promise<PasswordPolicy> {
  try {
    const { data } = await api.gateway.get<PasswordPolicy>(
      '/auth/password/policy',
    );
    if (
      typeof data?.token_expires_minutes !== 'number' ||
      typeof data?.password_min_length !== 'number' ||
      typeof data?.password_max_length !== 'number'
    ) {
      return DEFAULT_PASSWORD_POLICY;
    }
    return {
      reset_enabled: Boolean(data.reset_enabled),
      token_expires_minutes: data.token_expires_minutes,
      password_min_length: data.password_min_length,
      password_max_length: data.password_max_length,
    };
  } catch {
    return DEFAULT_PASSWORD_POLICY;
  }
}
