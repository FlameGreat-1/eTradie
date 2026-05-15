export { AuthProvider, useAuth } from './context/AuthContext';
export type {
  AuthUser,
  TokenPair,
  LoginRequest,
  RegisterRequest,
  OAuthStartRequest,
  OAuthStartResponse,
  OAuthCallbackRequest,
  OAuthCallbackResponse,
} from './types';
import type { AuthUser } from './types';

/**
 * Returns true when the user is exempt from all subscription-tier
 * checks. Admins are always exempt (the backend mirrors this in
 * every gating site); paying tiers (pro_byok, pro_managed) clear
 * the same bar because they have already paid for the feature.
 *
 * A nullish user (logged out, mid-load) is treated as restricted
 * so any gated surface degrades to the safe state until auth
 * resolves.
 *
 * Single source of truth for every Pro-gated component: a future
 * tier rename ("team", "enterprise", ...) is a one-line edit here.
 */
export function isTierUnrestricted(user: AuthUser | null | undefined): boolean {
  if (!user) return false;
  if (user.role === 'admin') return true;
  const tier = user.tier ?? 'free';
  return tier === 'pro_byok' || tier === 'pro_managed';
}

/**
 * Returns true when the user is an admin. Convenience helper kept
 * alongside isTierUnrestricted so callers that need the stricter
 * "admin only" check (e.g. hiding the entire Subscription tab
 * because admins do not have a subscription record at all) read
 * from the same module instead of inlining `user?.role === 'admin'`.
 */
export function isAdmin(user: AuthUser | null | undefined): boolean {
  return user?.role === 'admin';
}
// The `AuthProvider` literal-union type lives at
// `@/features/auth/types` and is intentionally NOT re-exported here
// to avoid name-shadowing with the React component of the same name
// also exported above.
export {
  startGoogleOAuth,
  completeGoogleOAuth,
  startGoogleLink,
  completeGoogleLink,
  unlinkGoogle,
} from './api/oauth';
export {
  requestPasswordReset,
  validateResetToken,
  resetPassword,
  getPasswordPolicy,
  DEFAULT_PASSWORD_POLICY,
} from './api/passwordReset';
export type {
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  PasswordPolicy,
  ValidateResetTokenRequest,
  ValidateResetTokenResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
} from './types';
export { useGoogleOAuth } from './hooks/useGoogleOAuth';
export type {
  OAuthLinkStartRequest,
  OAuthLinkStartResponse,
  OAuthLinkCallbackRequest,
  OAuthLinkCallbackResponse,
} from './types';
