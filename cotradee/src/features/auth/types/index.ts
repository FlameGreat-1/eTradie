export type AuthProvider = 'local' | 'google';

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'etradie';
  active: boolean;
  /**
   * How this account authenticates. "local" means username + password;
   * "google" means federated identity. Older gateway builds may omit
   * this field; consumers should default to "local" when absent.
   */
  auth_provider?: AuthProvider;
  /** Optional profile picture URL supplied by the identity provider. */
  avatar_url?: string;
  /**
   * Mirrors the identity provider's email-verification claim. Always
   * true for accounts created via Google.
   */
  email_verified?: boolean;
  tier?: 'free' | 'pro_byok' | 'pro_managed';
  status?: string;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  /** Always "Bearer" for the gateway's TokenPair shape. */
  token_type?: string;
  /** Access-token TTL in seconds. */
  expires_in?: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  user: AuthUser;
  tokens: TokenPair;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/* ── OAuth 2.0 ─────────────────────────────────────────── */

export interface OAuthStartRequest {
  /** Same-origin path the user should land on after a successful sign-in. */
  return_to?: string;
}

export interface OAuthStartResponse {
  authorize_url: string;
  state: string;
  /** Server-side TTL of the in-flight authorize record, in seconds. */
  expires_in: number;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
}

export interface OAuthCallbackResponse {
  user: AuthUser;
  tokens: TokenPair;
  is_new_user: boolean;
  /** Echoed back from the start-step record; safe to navigate to. */
  return_to: string;
}

/* ── Google account-linking (authenticated) ─────────────────────── */

/**
 * Begin a Google account-link from the settings page. The gateway
 * binds the minted state to the authenticated user server-side, so a
 * stolen state cannot be redeemed against a different account.
 */
export interface OAuthLinkStartRequest {
  /** Same-origin path the user should land on after a successful link. */
  return_to?: string;
}

export interface OAuthLinkStartResponse {
  authorize_url: string;
  state: string;
  /** Server-side TTL of the in-flight link record, in seconds. */
  expires_in: number;
}

export interface OAuthLinkCallbackRequest {
  code: string;
  state: string;
}

/**
 * Finish a Google account-link. The gateway returns the updated
 * profile so the dashboard can refresh AuthContext without a separate
 * /auth/me round-trip.
 */
export interface OAuthLinkCallbackResponse {
  user: AuthUser;
  /** Echoed back from the start-step record; safe to navigate to. */
  return_to: string;
}

/* ── Forgot / reset password ─────────────────────────────────────── */

export interface ForgotPasswordRequest {
  email: string;
}

/**
 * Gateway returns the same envelope whether the email exists or not,
 * so the SPA must NOT branch on the response to infer account state.
 * `status` is always 'accepted' on the happy path.
 */
export interface ForgotPasswordResponse {
  message: string;
  status: 'accepted';
}

export interface ValidateResetTokenRequest {
  token: string;
}

export interface ValidateResetTokenResponse {
  valid: boolean;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
}
