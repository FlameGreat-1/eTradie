import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export function useManagedTrades() {
  return useQuery({
    queryKey: ['management', 'trades'],
    queryFn: async () => {
      const { data } = await api.management.get('/api/v1/management/trades');
      return data.trades;
    },
    refetchInterval: 2_000,
  });
}

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
  });
}

export function usePerformanceMetrics(period = 'ALL_TIME') {
  return useQuery({
    queryKey: ['management', 'metrics', period],
    queryFn: async () => {
      const { data } = await api.management.get(`/api/v1/management/metrics?period=${period}`);
      return data;
    },
    refetchInterval: 10_000,
  });
}
