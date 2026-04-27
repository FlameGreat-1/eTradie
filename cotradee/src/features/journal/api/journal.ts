import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

/**
 * Active managed trades. Returns ALWAYS an array — callers can use
 * `data ?? []` safely and never need to check for undefined.
 *
 * Polled every 5 s as a safety net; realtime events PARTIAL_CLOSE /
 * TRADE_CLOSED / BREAKEVEN_SET / TRAILING_SL_MOVED / ORDER_FILLED
 * invalidate this key for instant updates.
 */
export function useManagedTrades() {
  return useQuery<unknown[]>({
    queryKey: ['management', 'trades'],
    queryFn: async () => {
      const { data } = await api.management.get('/api/v1/management/trades');
      const trades = (data && Array.isArray(data.trades) ? data.trades : []) as unknown[];
      return trades;
    },
    refetchInterval: 5_000,
    staleTime: 1_000,
  });
}

/**
 * Closed-trade journal. Default 30 s safety poll; WS events for
 * trade closes invalidate it instantly.
 */
export function useTradeJournal(params?: {
  limit?: number;
  offset?: number;
  symbol?: string;
  style?: string;
}) {
  const limit = params?.limit ?? 50;
  const offset = params?.offset ?? 0;

  return useQuery({
    queryKey: ['management', 'journal', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (params?.symbol) searchParams.append('symbol', params.symbol);
      if (params?.style) searchParams.append('style', params.style);

      const { data } = await api.management.get(`/api/v1/management/journal?${searchParams}`);
      return data;
    },
    refetchInterval: 30_000,
    staleTime: 5_000,
  });
}

/**
 * Aggregate performance metrics for a period (DAILY / WEEKLY / MONTHLY
 * / ALL_TIME). 15 s safety poll; WS pushes PARTIAL_CLOSE / TRADE_CLOSED
 * / PERFORMANCE_REPORT events that invalidate this key.
 */
export function usePerformanceMetrics(period = 'ALL_TIME') {
  return useQuery({
    queryKey: ['management', 'metrics', period],
    queryFn: async () => {
      const { data } = await api.management.get(`/api/v1/management/metrics?period=${period}`);
      return data;
    },
    refetchInterval: 15_000,
    staleTime: 2_000,
  });
}
