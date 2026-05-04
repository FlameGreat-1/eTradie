import { api } from '@/lib/axios';
import type {
  OAuthStartRequest,
  OAuthStartResponse,
  OAuthCallbackRequest,
  OAuthCallbackResponse,
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
