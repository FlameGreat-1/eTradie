import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { POLL_RETRY, adaptiveInterval } from '@/lib/queryHelpers';
import { useAuth } from '@/features/auth/context/AuthContext';
import type {
  PerformanceReviewHistoryPage,
  PerformanceReviewPeriod,
  PerformanceReviewRecord,
} from '../types';
import {
  generateReview,
  getLatestReview,
  getReviewById,
  listReviewHistory,
} from './client';

/**
 * Centralised query-key factory so cache invalidations after a
 * /generate mutation can be expressed declaratively.
 */
export const performanceReviewKeys = {
  all: ['performance-review'] as const,
  latest: (period: PerformanceReviewPeriod) =>
    ['performance-review', 'latest', period] as const,
  byId: (id: number) => ['performance-review', 'by-id', id] as const,
  history: (period: PerformanceReviewPeriod | 'all', offset: number, limit: number) =>
    ['performance-review', 'history', period, offset, limit] as const,
};

/**
 * Latest review for the given period. While the row is in status
 * 'generating' we poll every 6s so the SPA flips to the new review
 * within seconds of the gateway callback. Otherwise the safety poll
 * runs at 60s; manual mutations invalidate the key for instant updates.
 */
export function usePerformanceReviewLatest(period: PerformanceReviewPeriod) {
  const { isAuthenticated } = useAuth();
  return useQuery<PerformanceReviewRecord>({
    queryKey: performanceReviewKeys.latest(period),
    queryFn: () => getLatestReview(period),
    refetchInterval: (q) => {
      const data = q.state.data as PerformanceReviewRecord | undefined;
      if (data?.status === 'generating') return adaptiveInterval(6_000);
      return adaptiveInterval(60_000);
    },
    staleTime: 2_000,
    retry: POLL_RETRY,
    enabled: isAuthenticated,
  });
}

/**
 * Full review by id. Used by the history list to load the detail of
 * a row the user clicked into. Cache is long-lived (5 min) because
 * a 'ready' row is immutable on the server.
 */
export function usePerformanceReviewById(id: number | null | undefined) {
  const { isAuthenticated } = useAuth();
  return useQuery<PerformanceReviewRecord>({
    queryKey: performanceReviewKeys.byId(id ?? 0),
    queryFn: () => getReviewById(id as number),
    enabled: isAuthenticated && typeof id === 'number' && id > 0,
    staleTime: 5 * 60_000,
    retry: POLL_RETRY,
  });
}

/**
 * Paginated history list. Defaults to all periods (weekly + monthly
 * interleaved) ordered by updated_at DESC.
 */
export function usePerformanceReviewHistory(
  period?: PerformanceReviewPeriod,
  offset = 0,
  limit = 20,
) {
  const { isAuthenticated } = useAuth();
  return useQuery<PerformanceReviewHistoryPage>({
    queryKey: performanceReviewKeys.history(period ?? 'all', offset, limit),
    queryFn: () => listReviewHistory(period, offset, limit),
    enabled: isAuthenticated,
    staleTime: 5_000,
    retry: POLL_RETRY,
  });
}

/**
 * Mutation that triggers a fresh review generation. The gateway
 * returns 202 Accepted; the SPA invalidates the /latest query so
 * the polling loop picks up the new 'generating' row immediately
 * and the progress banner renders.
 */
export function useGeneratePerformanceReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (period: PerformanceReviewPeriod) => generateReview(period),
    onSuccess: (_data, period) => {
      qc.invalidateQueries({ queryKey: performanceReviewKeys.latest(period) });
      qc.invalidateQueries({ queryKey: ['performance-review', 'history'] });
    },
  });
}
