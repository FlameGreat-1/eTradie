import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';
import {
  getTradingSystem,
  getTradingSystemSchema,
  getTradingSystemStatus,
  resetTradingSystem,
  saveTradingSystem,
  skipTradingSystem,
} from './client';
import type {
  TradingSystemProfile,
  TradingSystemRecord,
  TradingSystemSchemaCatalogue,
  TradingSystemStatusView,
} from '../types';

/**
 * Query keys. Exported so the onboarding card and the dashboard can
 * invalidate selectively without depending on string literals
 * scattered through component code.
 */
export const tradingSystemKeys = {
  all: ['trading-system'] as const,
  profile: () => [...tradingSystemKeys.all, 'profile'] as const,
  status: () => [...tradingSystemKeys.all, 'status'] as const,
  schema: () => [...tradingSystemKeys.all, 'schema'] as const,
} as const;

/**
 * Full profile. Used by the view page and the builder's edit mode to
 * hydrate the form with the user's existing answers.
 */
export function useTradingSystem(
  options?: Omit<UseQueryOptions<TradingSystemRecord>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TradingSystemRecord>({
    queryKey: tradingSystemKeys.profile(),
    queryFn: getTradingSystem,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Lightweight status projection. Used by the dashboard onboarding
 * checklist on every mount; deliberately short stale time so the
 * checklist updates the moment the user finishes the builder in
 * another tab. Cheap on the server because it never hydrates the
 * JSONB profile column.
 */
export function useTradingSystemStatus(
  options?: Omit<UseQueryOptions<TradingSystemStatusView>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TradingSystemStatusView>({
    queryKey: tradingSystemKeys.status(),
    queryFn: getTradingSystemStatus,
    staleTime: 10 * 1000, // 10s
    ...options,
  });
}

/**
 * Closed-enum catalogue. Cached effectively forever because the
 * server-side values only change with a deploy that bumps the schema
 * version (which already busts the cache via the version field).
 */
export function useTradingSystemSchema(
  options?: Omit<UseQueryOptions<TradingSystemSchemaCatalogue>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TradingSystemSchemaCatalogue>({
    queryKey: tradingSystemKeys.schema(),
    queryFn: getTradingSystemSchema,
    staleTime: Infinity,
    gcTime: Infinity,
    ...options,
  });
}

/**
 * Save (or regenerate) the user's profile. Bumps version, sets
 * status='active'. Invalidates BOTH the full profile cache and the
 * lightweight status cache so the onboarding checklist updates
 * immediately.
 */
export function useSaveTradingSystem(
  options?: UseMutationOptions<TradingSystemRecord, unknown, TradingSystemProfile>,
) {
  const qc = useQueryClient();
  return useMutation<TradingSystemRecord, unknown, TradingSystemProfile>({
    mutationFn: (profile) => saveTradingSystem(profile),
    onSuccess: (data, variables, context) => {
      qc.setQueryData(tradingSystemKeys.profile(), data);
      qc.invalidateQueries({ queryKey: tradingSystemKeys.status() });
      options?.onSuccess?.(data, variables, context as any, undefined as any);
    },
    ...options,
  });
}

/**
 * Skip onboarding. Does NOT touch an existing active profile (the
 * server preserves it). Invalidates the status cache so the
 * onboarding checklist removes its prompt.
 */
export function useSkipTradingSystem(
  options?: UseMutationOptions<TradingSystemStatusView, unknown, void>,
) {
  const qc = useQueryClient();
  return useMutation<TradingSystemStatusView, unknown, void>({
    mutationFn: () => skipTradingSystem(),
    onSuccess: (data, variables, context) => {
      qc.setQueryData(tradingSystemKeys.status(), data);
      options?.onSuccess?.(data, variables, context as any, undefined as any);
    },
    ...options,
  });
}

/**
 * Clear the profile back to status='none'. Used by the view page's
 * "start over" affordance. Invalidates everything because both the
 * full profile and the status projection change.
 */
export function useResetTradingSystem(
  options?: UseMutationOptions<void, unknown, void>,
) {
  const qc = useQueryClient();
  return useMutation<void, unknown, void>({
    mutationFn: () => resetTradingSystem(),
    onSuccess: (data, variables, context) => {
      qc.invalidateQueries({ queryKey: tradingSystemKeys.all });
      options?.onSuccess?.(data, variables, context as any, undefined as any);
    },
    ...options,
  });
}
