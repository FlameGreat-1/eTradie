import { api } from '@/lib/axios';
import type {
  OAuthStartRequest,
  OAuthStartResponse,
  OAuthCallbackRequest,
  OAuthCallbackResponse,
  OAuthLinkStartRequest,
  OAuthLinkStartResponse,
  OAuthLinkCallbackRequest,
  OAuthLinkCallbackResponse,
} from '../types';

/**
 * Begin a Google OAuth 2.0 sign-in.
 *
 * The gateway mints a single-use state, nonce, and PKCE verifier,
 * persists them server-side keyed by `state`, and returns the URL the
 * browser must navigate to in order to obtain user consent. The state
 * value MUST be stashed by the caller (see oauthStorage.ts) so the
 * callback page can verify the round-trip.
 */
export async function startGoogleOAuth(
  payload: OAuthStartRequest = {},
): Promise<OAuthStartResponse> {
  const { data } = await api.gateway.post<OAuthStartResponse>(
    '/auth/oauth/google/start',
    payload,
  );
  return data;
}

/**
 * Finish a Google OAuth 2.0 sign-in.
 *
 * Posts the `code` + `state` returned by Google to the gateway, which
 * exchanges the code for an ID token, verifies it against Google's
 * JWKS, resolves or creates the eTradie user, and returns the same
 * TokenPair shape produced by `/auth/login` and `/auth/register`.
 */
export async function completeGoogleOAuth(
  payload: OAuthCallbackRequest,
): Promise<OAuthCallbackResponse> {
  const { data } = await api.gateway.post<OAuthCallbackResponse>(
    '/auth/oauth/google/callback',
    payload,
  );
  return data;
}

/**
 * Begin a Google account-link for the *currently authenticated* user.
 *
 * Distinct from startGoogleOAuth: the gateway binds the minted state
 * to the bearer-token subject server-side, so the link can only ever
 * complete against the same user that started it. This is the
 * standard mitigation for OAuth account-linking CSRF and is the
 * reason this is a separate endpoint rather than a flag on the
 * sign-in start.
 */
export async function startGoogleLink(
  payload: OAuthLinkStartRequest = {},
): Promise<OAuthLinkStartResponse> {
  const { data } = await api.gateway.post<OAuthLinkStartResponse>(
    '/auth/oauth/google/link/start',
    payload,
  );
  return data;
}

/**
 * Finish a Google account-link.
 *
 * Posts the `code` + `state` returned by Google to the gateway, which
 * exchanges the code, verifies the ID token, and binds the resolved
 * `sub` claim to the authenticated user. Returns the updated profile
 * so AuthContext can refresh without a separate /auth/me round-trip.
 */
export async function completeGoogleLink(
  payload: OAuthLinkCallbackRequest,
): Promise<OAuthLinkCallbackResponse> {
  const { data } = await api.gateway.post<OAuthLinkCallbackResponse>(
    '/auth/oauth/google/link/callback',
    payload,
  );
  return data;
}

/**
 * Remove the Google identity binding from the authenticated user.
 * The user retains their local password credentials and remains able
 * to sign in with username + password afterwards.
 */
export async function unlinkGoogle(): Promise<void> {
  await api.gateway.delete('/auth/oauth/google/link');
}
