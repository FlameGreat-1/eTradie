import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

export function useSymbols() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['symbols'],
    queryFn: async () => {
      const { data } = await api.gateway.get<{ symbols: string[]; source: string }>('/api/v1/symbols');
      return data;
    },
    enabled: isAuthenticated,
  });
}

export interface BrokerSymbol {
  name: string;
  description: string;
  path: string;
}

type BrokerSymbolsResponse = { symbols: BrokerSymbol[]; count: number };

export interface UseBrokerSymbolsOptions {
  /**
   * TanStack Query refetchInterval passthrough. Accepts a fixed
   * number of milliseconds, `false` to disable polling, or a
   * function receiving the query and returning either. Used by
   * SymbolsStep to poll every 3 s while the catalog is still empty
   * (the broker_symbols table populates asynchronously immediately
   * after the broker-connect step). The default (omitted) preserves
   * a single fetch with the 5-minute staleTime, which is what the
   * header dropdown and settings page want.
   */
  refetchInterval?:
    | number
    | false
    | ((query: { state: { data: BrokerSymbolsResponse | undefined } }) => number | false);
}

export function useBrokerSymbols(options: UseBrokerSymbolsOptions = {}) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker-symbols'],
    queryFn: async () => {
      const { data } = await api.engine.get<BrokerSymbolsResponse>('/api/broker/symbols');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes — matches backend cache TTL
    enabled: isAuthenticated,
    refetchInterval: options.refetchInterval,
  });
}

export function useUpdateSymbols() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (symbols: string[]) => {
      const { data } = await api.gateway.put('/api/v1/symbols', { symbols });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['symbols'] }),
  });
}
