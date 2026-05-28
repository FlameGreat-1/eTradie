/**
 * Admin tier-quota policy hooks.
 *
 * Backs the AdminQuotaPolicyPanel at
 * cotradee/src/features/admin/components/AdminQuotaPolicyPanel.tsx
 * which lets an admin edit the platform-managed LLM quota policy
 * persisted in the `tier_quota_policies` Postgres table (migration
 * 0028). The gateway-side endpoints live at
 * src/gateway/internal/server/admin_quota_handler.go (Step 6).
 *
 * Wire shapes mirror billingstore.QuotaPolicyRow one-for-one. Drift
 * between the two would surface as silent dropped fields on Upsert,
 * so any change here MUST be paired with a change on the Go side.
 *
 * Audit ref: ADMIN-QUOTA-12.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth, isAdmin } from '@/features/auth';

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

/**
 * Canonical tier names enforced by the migration's CHECK constraint.
 * Exported so the panel can iterate without hard-coding strings.
 */
export const QUOTA_TIERS = ['pro_managed', 'admin', 'pro_byok', 'free'] as const;
export type QuotaTier = (typeof QUOTA_TIERS)[number];

/**
 * One row of tier_quota_policies. Field names match the Go-side
 * QuotaPolicyRow JSON tags exactly; do not rename without updating
 * src/billing/store/quota_policy.go in the same commit.
 */
export interface QuotaPolicyRow {
  tier: QuotaTier | string;
  daily_input_tokens: number;
  daily_output_tokens: number;
  monthly_input_tokens: number;
  monthly_output_tokens: number;
  max_input_tokens_per_call: number;
  soft_cap_percent: number;
  reservation_ttl_seconds: number;
  allowed_models: string[];
  enforced: boolean;
  updated_at: string;
  updated_by?: string | null;
}

/**
 * Response shape of GET /api/v1/admin/quota/policies (the list
 * endpoint). canonical_tiers is the same constant as QUOTA_TIERS
 * above; we still consume it from the server so a future tier
 * addition only requires editing the migration + the seed + this
 * constant (which auto-syncs via the panel's canonical_tiers read).
 */
export interface AdminQuotaPoliciesResponse {
  rows: QuotaPolicyRow[];
  canonical_tiers: string[];
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useAdminGuard(): boolean {
  const { user, isAuthenticated } = useAuth();
  return Boolean(isAuthenticated && isAdmin(user));
}

/**
 * List every tier's quota policy in canonical order (pro_managed,
 * admin, pro_byok, free). Disabled for non-admins so the gateway
 * 403 is never even exercised by the SPA.
 */
export function useAdminQuotaPolicies() {
  const enabled = useAdminGuard();
  return useQuery<AdminQuotaPoliciesResponse>({
    queryKey: ['admin', 'quota', 'policies'],
    queryFn: async () => {
      const { data } = await api.gateway.get('/api/v1/admin/quota/policies');
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

/**
 * Fetch one tier's quota policy. Used by deep-link refetches after
 * Upsert; the panel mostly consumes useAdminQuotaPolicies above.
 */
export function useAdminQuotaPolicy(tier: QuotaTier | string | null | undefined) {
  const enabled = useAdminGuard() && Boolean(tier);
  return useQuery<QuotaPolicyRow>({
    queryKey: ['admin', 'quota', 'policies', tier],
    queryFn: async () => {
      const { data } = await api.gateway.get(
        `/api/v1/admin/quota/policies/${encodeURIComponent(tier!)}`,
      );
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

/**
 * Upsert one tier's quota policy. The PUT body is the full
 * QuotaPolicyRow shape; the gateway's path :tier wins over body.tier
 * so a stale value in the editor cannot overwrite the wrong row.
 *
 * On success invalidates BOTH:
 *   - ['admin', 'quota', 'policies']           (the list query)
 *   - ['admin', 'quota', 'policies', tier]     (the single-row query)
 * so every consumer refetches and sees the updated_at + updated_by
 * audit fields populated by the DB.
 */
export function useUpdateAdminQuotaPolicy() {
  const qc = useQueryClient();
  return useMutation<QuotaPolicyRow, unknown, { tier: string; row: QuotaPolicyRow }>({
    mutationFn: async ({ tier, row }) => {
      const { data } = await api.gateway.put(
        `/api/v1/admin/quota/policies/${encodeURIComponent(tier)}`,
        row,
      );
      return data;
    },
    onSuccess: (_data, { tier }) => {
      void qc.invalidateQueries({ queryKey: ['admin', 'quota', 'policies'] });
      void qc.invalidateQueries({ queryKey: ['admin', 'quota', 'policies', tier] });
    },
  });
}
