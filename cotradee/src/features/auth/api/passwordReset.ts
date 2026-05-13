import { api } from '@/lib/axios';
import type {
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  ValidateResetTokenRequest,
  ValidateResetTokenResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
} from '../types';

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
