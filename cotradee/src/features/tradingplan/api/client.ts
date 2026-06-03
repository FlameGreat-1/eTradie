import type { AxiosError } from 'axios';
import { api } from '@/lib/axios';
import {
  TradingPlanValidationError,
  type GenerateOptions,
  type TradingPlan,
  type TradingPlanRecord,
  type TradingPlanStatusView,
} from '../types';

/**
 * Thin wrappers over the gateway's /api/v1/trading-plan surface.
 *
 * Cookie authentication, CSRF token stamping, and silent 401 refresh
 * are inherited from the shared axios instance in @/lib/axios.
 */

const BASE = '/api/v1/trading-plan';

export async function getTradingPlan(): Promise<TradingPlanRecord> {
  // Forward the browser IANA timezone so the gateway renders the
  // auto-filled journal Date cell in the trader's local time, never
  // raw UTC. A missing/invalid tz degrades to UTC server-side.
  const params: Record<string, string> = {};
  const tz = resolveBrowserTimeZone();
  if (tz) params.tz = tz;
  const { data } = await api.gateway.get<TradingPlanRecord>(BASE, { params });
  return data;
}

// resolveBrowserTimeZone returns the browser's IANA timezone
// (e.g. "Europe/London"), or "" when the Intl API is unavailable so
// the caller omits the tz param and the gateway falls back to UTC.
function resolveBrowserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || '';
  } catch {
    return '';
  }
}

export async function getTradingPlanStatus(): Promise<TradingPlanStatusView> {
  const { data } = await api.gateway.get<TradingPlanStatusView>(`${BASE}/status`);
  return data;
}

/**
 * Kicks off async generation. Returns 202 quickly; the SPA then polls
 * /status until it transitions to 'active' (or 'failed').
 */
export async function generateTradingPlan(
  opts: GenerateOptions = {},
): Promise<{ status: 'generating'; message?: string }> {
  const body: Record<string, unknown> = {};
  if (opts.fallback_balance != null && opts.fallback_balance > 0) {
    body.fallback_balance = opts.fallback_balance;
  }
  if (opts.fallback_currency) {
    body.fallback_currency = opts.fallback_currency.toUpperCase();
  }
  const { data } = await api.gateway.post<{ status: 'generating'; message?: string }>(
    `${BASE}/generate`,
    Object.keys(body).length > 0 ? body : undefined,
  );
  return data;
}

/**
 * Persist in-app manual edits (journal rows, scorecard scores, etc.).
 * Does NOT trigger an LLM call; the gateway saves the new content and
 * leaves version unchanged.
 */
export async function updateTradingPlan(
  plan: TradingPlan,
): Promise<TradingPlanRecord> {
  try {
    const { data } = await api.gateway.put<TradingPlanRecord>(BASE, plan);
    return data;
  } catch (err) {
    throw translateValidationError(err);
  }
}

export async function resetTradingPlan(): Promise<void> {
  await api.gateway.post(`${BASE}/reset`);
}

function translateValidationError(err: unknown): unknown {
  const axErr = err as AxiosError<{ error?: string; fields?: Record<string, string> }>;
  if (axErr?.response?.status !== 422) {
    return err;
  }
  const body = axErr.response.data ?? {};
  const fields = body.fields ?? {};
  const message = body.error || 'Trading plan is invalid';
  return new TradingPlanValidationError(message, fields);
}
