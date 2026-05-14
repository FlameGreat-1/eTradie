import type { AxiosError } from 'axios';
import { api } from '@/lib/axios';
import {
  TradingSystemValidationError,
  type TradingSystemProfile,
  type TradingSystemRecord,
  type TradingSystemSchemaCatalogue,
  type TradingSystemStatusView,
} from '../types';

/**
 * Thin wrappers over the gateway's /api/v1/trading-system surface.
 *
 * Cookie authentication, CSRF token stamping, and silent 401 refresh
 * are inherited from the shared axios instance in @/lib/axios. The
 * only auth-related work this module does is translate the gateway's
 * 422 validation envelope into a typed TradingSystemValidationError
 * so the builder UI can render field-level messages inline.
 */

const BASE = '/api/v1/trading-system';

export async function getTradingSystem(): Promise<TradingSystemRecord> {
  const { data } = await api.gateway.get<TradingSystemRecord>(BASE);
  return data;
}

export async function getTradingSystemStatus(): Promise<TradingSystemStatusView> {
  const { data } = await api.gateway.get<TradingSystemStatusView>(`${BASE}/status`);
  return data;
}

export async function getTradingSystemSchema(): Promise<TradingSystemSchemaCatalogue> {
  const { data } = await api.gateway.get<TradingSystemSchemaCatalogue>(`${BASE}/schema`);
  return data;
}

export async function saveTradingSystem(
  profile: TradingSystemProfile,
): Promise<TradingSystemRecord> {
  try {
    const { data } = await api.gateway.put<TradingSystemRecord>(BASE, profile);
    return data;
  } catch (err) {
    throw translateValidationError(err);
  }
}

export async function skipTradingSystem(): Promise<TradingSystemStatusView> {
  const { data } = await api.gateway.post<TradingSystemStatusView>(`${BASE}/skip`);
  return data;
}

export async function resetTradingSystem(): Promise<void> {
  await api.gateway.post(`${BASE}/reset`);
}

// Map the gateway's 422 envelope to a typed error the builder can
// branch on. Any other error (network, 401, 500) is re-thrown
// unchanged so the shared interceptor in @/lib/axios handles toasts,
// silent refresh, and logout broadcasting.
function translateValidationError(err: unknown): unknown {
  const axErr = err as AxiosError<{ error?: string; fields?: Record<string, string> }>;
  if (axErr?.response?.status !== 422) {
    return err;
  }
  const body = axErr.response.data ?? {};
  const fields = body.fields ?? {};
  const message = body.error || 'Trading system profile is invalid';
  return new TradingSystemValidationError(message, fields);
}
