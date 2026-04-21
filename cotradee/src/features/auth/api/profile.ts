import { api } from '@/lib/axios';
import type { AuthUser, ChangePasswordRequest } from '../types';

export async function fetchProfile(): Promise<AuthUser> {
  const { data } = await api.gateway.get<AuthUser>('/auth/me');
  return data;
}

export async function changePassword(payload: ChangePasswordRequest): Promise<void> {
  await api.gateway.put('/auth/me/password', payload);
}

export async function logout(refreshToken?: string): Promise<void> {
  await api.gateway.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
}

export async function logoutAll(): Promise<void> {
  await api.gateway.post('/auth/logout-all');
}
