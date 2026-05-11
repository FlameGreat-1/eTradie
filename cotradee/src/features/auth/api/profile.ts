import { api } from '@/lib/axios';
import type { AuthUser, ChangePasswordRequest } from '../types';

export async function fetchProfile(): Promise<AuthUser> {
  const { data } = await api.gateway.get<AuthUser>('/auth/me');
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
