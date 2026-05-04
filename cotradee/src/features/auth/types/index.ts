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
