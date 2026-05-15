import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth, isAdmin } from '@/features/auth';

// ---------------------------------------------------------------------------
// Response shapes (mirror Go billingstore.Admin* types one-for-one).
// ---------------------------------------------------------------------------

export interface AdminSubscriptionRow {
  user_id: string;
  username: string;
  email: string;
  tier: string;
  status: string;
  payment_provider: string | null;
  provider_customer_id: string | null;
  provider_subscription_id: string | null;
  current_period_end: string | null;
  event_timestamp: string;
  created_at: string;
  updated_at: string;
}

export interface AdminSubscriptionEventRow {
  id: number;
  user_id: string;
  username: string;
  email: string;
  provider: string;
  event_name: string;
  event_id: string;
  previous_tier: string;
  new_tier: string;
  previous_status: string;
  new_status: string;
  event_timestamp: string;
  created_at: string;
}

export interface AdminLLMUsageRow {
  user_id: string;
  username: string;
  email: string;
  tier: string;
  status: string;
  input_tokens_today: number;
  output_tokens_today: number;
  input_tokens_month: number;
  output_tokens_month: number;
  blocked_today: number;
  blocked_month: number;
  monthly_window_start: string;
  last_metered_at: string | null;
  llm_tokens_used_total: number;
}

export interface AdminLLMAggregate {
  input_tokens_today: number;
  output_tokens_today: number;
  input_tokens_month: number;
  output_tokens_month: number;
  blocked_month: number;
  active_users_month: number;
  held_reservations: number;
  total_reservations: number;
}

export interface Paginated<T> {
  rows: T[];
  total: number;
  page: number;
  size: number;
}

export interface SubscriptionFilter {
  tier?: string;
  status?: string;
  provider?: string;
  search?: string;
}

export interface TransactionFilter {
  provider?: string;
  event_name?: string;
  user_id?: string;
  search?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// buildParams strips empty / undefined fields so a request URL never
// carries "?search=&tier=". Stable ordering produces stable query keys.
function buildParams(filter: Record<string, unknown>, page: number, size: number): URLSearchParams {
  const sp = new URLSearchParams();
  Object.keys(filter)
    .sort()
    .forEach((k) => {
      const v = filter[k];
      if (v !== undefined && v !== null && String(v).trim() !== '') {
        sp.set(k, String(v));
      }
    });
  sp.set('page', String(page));
  sp.set('size', String(size));
  return sp;
}

function useAdminGuard(): boolean {
  const { user, isAuthenticated } = useAuth();
  return Boolean(isAuthenticated && isAdmin(user));
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useAdminSubscriptions(
  filter: SubscriptionFilter,
  page: number,
  size: number,
) {
  const enabled = useAdminGuard();
  const params = buildParams(filter as Record<string, unknown>, page, size);
  return useQuery<Paginated<AdminSubscriptionRow>>({
    queryKey: ['admin', 'billing', 'subscriptions', params.toString()],
    queryFn: async () => {
      const { data } = await api.gateway.get(
        `/api/v1/admin/billing/subscriptions?${params.toString()}`,
      );
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useAdminTransactions(
  filter: TransactionFilter,
  page: number,
  size: number,
) {
  const enabled = useAdminGuard();
  const params = buildParams(filter as Record<string, unknown>, page, size);
  return useQuery<Paginated<AdminSubscriptionEventRow>>({
    queryKey: ['admin', 'billing', 'transactions', params.toString()],
    queryFn: async () => {
      const { data } = await api.gateway.get(
        `/api/v1/admin/billing/transactions?${params.toString()}`,
      );
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useAdminUserTransactions(userID: string | null, limit = 100) {
  const enabled = useAdminGuard() && Boolean(userID);
  return useQuery<{ rows: AdminSubscriptionEventRow[]; user_id: string }>({
    queryKey: ['admin', 'billing', 'user-transactions', userID, limit],
    queryFn: async () => {
      const { data } = await api.gateway.get(
        `/api/v1/admin/billing/subscriptions/${encodeURIComponent(userID!)}/events?limit=${limit}`,
      );
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useAdminLLMUsage(search: string, page: number, size: number) {
  const enabled = useAdminGuard();
  const params = buildParams({ search } as Record<string, unknown>, page, size);
  return useQuery<Paginated<AdminLLMUsageRow>>({
    queryKey: ['admin', 'billing', 'llm-usage', params.toString()],
    queryFn: async () => {
      const { data } = await api.gateway.get(
        `/api/v1/admin/billing/llm-usage?${params.toString()}`,
      );
      return data;
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useAdminLLMAggregate() {
  const enabled = useAdminGuard();
  return useQuery<AdminLLMAggregate>({
    queryKey: ['admin', 'billing', 'llm-aggregate'],
    queryFn: async () => {
      const { data } = await api.gateway.get('/api/v1/admin/billing/llm-usage/aggregate');
      return data;
    },
    enabled,
    staleTime: 60_000,
  });
}
