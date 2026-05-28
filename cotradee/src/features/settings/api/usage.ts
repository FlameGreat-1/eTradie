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
 * Returns null for the two EXPECTED silent cases:
 *   - 404: no billing_usage row yet (BYOK / first-time visitor).
 *   - 401: cookie refresh in flight; the axios interceptor will
 *          rotate and re-dispatch the request transparently.
 *
 * Throws for every other status (notably 503 from a transient
 * gateway DB issue) so React Query's normal retry-with-backoff
 * kicks in and the consumer can render an error state instead of
 * silently disappearing. The 503 is now a distinct, recoverable
 * signal -- AUDIT-V2-3 made the gateway return it on transient
 * policy lookup failures; pretending it was a 404 hid real outages.
 *
 * Audit ref: ADMIN-QUOTA-AUDIT-V2-5.
 */
export async function getLLMUsageSnapshot(): Promise<LLMUsageSnapshot | null> {
  try {
    const { data } = await api.gateway.get<LLMUsageSnapshot>(
      '/api/v1/billing/usage',
    );
    return data;
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404 || status === 401) {
      return null;
    }
    // Anything else (notably 503): let TanStack Query observe the
    // error so retry-with-backoff fires and the panel can render
    // an error state instead of vanishing.
    // eslint-disable-next-line no-console
    console.warn('[UsagePanel] usage snapshot fetch failed', {
      status,
      error: err,
    });
    throw err;
  }
}
