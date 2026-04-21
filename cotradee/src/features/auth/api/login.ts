import { api } from '@/lib/axios';
import type { LoginRequest, TokenPair } from '../types';

export async function login(payload: LoginRequest): Promise<TokenPair> {
  const { data } = await api.gateway.post<TokenPair>('/auth/login', payload);
  return data;
}
