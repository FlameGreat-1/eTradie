import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';
import {
  generateTradingPlan,
  getTradingPlan,
  getTradingPlanStatus,
  resetTradingPlan,
  updateTradingPlan,
} from './client';
import type {
  GenerateOptions,
  TradingPlan,
  TradingPlanRecord,
  TradingPlanStatusView,
} from '../types';

export const tradingPlanKeys = {
  all: ['trading-plan'] as const,
  plan: () => [...tradingPlanKeys.all, 'plan'] as const,
  status: () => [...tradingPlanKeys.all, 'status'] as const,
} as const;

/**
 * Full plan. Used by the Trading Plan view page.
 */
export function useTradingPlan(
  options?: Omit<UseQueryOptions<TradingPlanRecord>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TradingPlanRecord>({
    queryKey: tradingPlanKeys.plan(),
    queryFn: getTradingPlan,
    staleTime: 30 * 1000,
    ...options,
  });
}

/**
 * Lightweight status projection. The hook auto-polls while the plan
 * is generating so the SPA transitions smoothly to the rendered
 * workbook the moment the engine callback persists the plan. Polling
 * stops as soon as status becomes 'active' or 'failed' to avoid
 * burning gateway capacity.
 */
export function useTradingPlanStatus(
  options?: Omit<UseQueryOptions<TradingPlanStatusView>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TradingPlanStatusView>({
    queryKey: tradingPlanKeys.status(),
    queryFn: getTradingPlanStatus,
    staleTime: 5 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data;
      // refetchInterval is invoked with the query object in TanStack v5.
      if (data?.status === 'generating') return 3000;
      return false;
    },
    refetchIntervalInBackground: false,
    ...options,
  });
}

/**
 * Trigger an async generation. The mutation resolves the moment the
 * gateway accepts the request (HTTP 202); the actual plan content
 * arrives later via the polling status hook.
 */
export function useGenerateTradingPlan(
  options?: UseMutationOptions<
    { status: 'generating'; message?: string },
    unknown,
    GenerateOptions | undefined
  >,
) {
  const qc = useQueryClient();
  return useMutation<
    { status: 'generating'; message?: string },
    unknown,
    GenerateOptions | undefined
  >({
    mutationFn: (opts) => generateTradingPlan(opts ?? {}),
    onSuccess: (data, variables, context) => {
      // Optimistically mark the cached status as generating so the
      // UI flips instantly; the next poll confirms.
      qc.setQueryData<TradingPlanStatusView | undefined>(
        tradingPlanKeys.status(),
        (prev) => ({
          status: 'generating',
          version: prev?.version ?? 0,
          has_plan: !!prev?.has_plan,
          updated_at: prev?.updated_at,
        }),
      );
      qc.invalidateQueries({ queryKey: tradingPlanKeys.plan() });
      options?.onSuccess?.(data, variables, context);
    },
    ...options,
  });
}

/**
 * Persist a manual edit. Optimistically updates the cached plan so
 * the table feels instant; the invalidation guarantees the cache
 * eventually matches the server-side row.
 */
export function useUpdateTradingPlan(
  options?: UseMutationOptions<TradingPlanRecord, unknown, TradingPlan>,
) {
  const qc = useQueryClient();
  return useMutation<TradingPlanRecord, unknown, TradingPlan>({
    mutationFn: (plan) => updateTradingPlan(plan),
    onSuccess: (data, variables, context) => {
      qc.setQueryData(tradingPlanKeys.plan(), data);
      qc.invalidateQueries({ queryKey: tradingPlanKeys.status() });
      options?.onSuccess?.(data, variables, context);
    },
    ...options,
  });
}

export function useResetTradingPlan(
  options?: UseMutationOptions<void, unknown, void>,
) {
  const qc = useQueryClient();
  return useMutation<void, unknown, void>({
    mutationFn: () => resetTradingPlan(),
    onSuccess: (data, variables, context) => {
      qc.invalidateQueries({ queryKey: tradingPlanKeys.all });
      options?.onSuccess?.(data, variables, context);
    },
    ...options,
  });
}
