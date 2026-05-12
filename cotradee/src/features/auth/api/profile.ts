import { api } from '@/lib/axios';
import type { AuthUser, ChangePasswordRequest } from '../types';

/**
 * Probe the gateway for the currently-authenticated user.
 *
 * /auth/me is the canonical 'who am I?' endpoint and is called on
 * every app mount by AuthContext to decide between the public and
 * the authenticated surface. For an unauthenticated visitor the
 * gateway returns 401 — this is the documented success path for
 * the guest render, NOT an error condition.
 *
 * To keep the console quiet on guest mount we tell axios that 401 is
 * a valid response (via validateStatus) and then translate it back
 * into a typed thrown error here. AuthContext.loadUser already wraps
 * this call in try/catch and maps any throw to setUser(null), so the
 * external contract is unchanged: the only effect is that the browser
 * console no longer logs a stack trace for the expected guest-401.
 *
 * The global axios response interceptor (see cotradee/src/lib/axios.ts)
 * also skips its silent-refresh path for any URL starting with /auth/,
 * so a 401 here cannot trigger the refresh-then-redirect loop fixed
 * earlier on UpgradeModal. This module relies on that skip path; do
 * not reintroduce auth-state-dependent logic here.
 */
export async function fetchProfile(): Promise<AuthUser> {
  const { status, data } = await api.gateway.get<AuthUser>('/auth/me', {
    // Accept both 200 (authenticated) and 401 (guest) as non-throwing
    // outcomes. Any other status is treated by axios as an error and
    // throws, preserving the genuine-failure path (5xx, network, CORS).
    validateStatus: (s) => s === 200 || s === 401,
  });
  if (status === 401) {
    // Marker error consumed only by AuthContext's loadUser catch. The
    // string is stable so callers that want to distinguish 'guest'
    // from 'transport failure' in future can match on it without
    // depending on the axios surface.
    throw new Error('unauthenticated');
  }
  return data;
}

export async function changePassword(payload: ChangePasswordRequest): Promise<void> {
  await api.gateway.put('/auth/me/password', payload);
}

// Post-Batch-11 the gateway reads the refresh token from the HttpOnly
// refresh_token cookie. Passing it in the JSON body is unnecessary
// (and undesirable: JS does not have access to it any more). The
// gateway logout handler clears all three auth cookies on the
// response so the browser jar is left in a clean state.
export async function logout(): Promise<void> {
  await api.gateway.post('/auth/logout', {});
}

export async function logoutAll(): Promise<void> {
  await api.gateway.post('/auth/logout-all');
}
