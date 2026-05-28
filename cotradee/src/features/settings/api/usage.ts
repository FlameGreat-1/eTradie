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
 *
 * Audit ref: ADMIN-QUOTA-AUDIT-16. We now log a console warning for
 * unexpected statuses so a real 500 / 503 surfaces in devtools and any
 * Sentry-style error reporter, while still degrading gracefully on
 * the user-facing side.
 */
export async function getLLMUsageSnapshot(): Promise<LLMUsageSnapshot | null> {
  try {
    const { data } = await api.gateway.get<LLMUsageSnapshot>(
      '/api/v1/billing/usage',
    );
    return data;
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    // 404 is the expected response when the gateway has no row for
    // this user yet (BYOK / first-time visitor). 401 is handled by the
    // global axios interceptor (silent refresh). Anything else is a
    // real failure the operator should see.
    if (status && status !== 404 && status !== 401) {
      // eslint-disable-next-line no-console
      console.warn('[UsagePanel] usage snapshot fetch failed', {
        status,
        error: err,
      });
    }
    return null;
  }
}
