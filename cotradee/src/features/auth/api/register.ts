import { api } from '@/lib/axios';
import type { RegisterRequest, RegisterResponse } from '../types';

export async function register(payload: RegisterRequest): Promise<RegisterResponse> {
  const { data } = await api.gateway.post<RegisterResponse>('/auth/register', payload);
  return data;
}
