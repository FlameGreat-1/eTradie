import { api } from '@/lib/axios';

/**
 * LLM usage snapshot returned by GET /api/v1/billing/usage.
 * Mirrors the Go store.LLMUsageSnapshot shape.
 */
export interface LLMUsageSnapshot {
  input_tokens_today: number;
  output_tokens_today: number;
  input_tokens_month: number;
  output_tokens_month: number;
  blocked_today: number;
  blocked_month: number;
  monthly_window_start: string; // ISO-8601
  last_metered_at: string | null; // ISO-8601 or null
  daily_input_limit: number;
  daily_output_limit: number;
  monthly_input_limit: number;
  monthly_output_limit: number;
  soft_cap_percent: number;
  quota_enforced: boolean;
}

/**
 * Fetch the authenticated user's LLM token usage snapshot.
 *
 * Returns null when the endpoint is unavailable (e.g. the user is on
 * the free tier and the gateway returns 404, or the network is down).
 * The caller renders nothing rather than an error state so the billing
 * section degrades gracefully.
 */
export async function getLLMUsageSnapshot(): Promise<LLMUsageSnapshot | null> {
  try {
    const { data } = await api.gateway.get<LLMUsageSnapshot>(
      '/api/v1/billing/usage',
    );
    return data;
  } catch {
    return null;
  }
}
