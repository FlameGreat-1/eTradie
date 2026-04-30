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

export function useBrokerSymbols() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker-symbols'],
    queryFn: async () => {
      const { data } = await api.engine.get<{ symbols: BrokerSymbol[]; count: number }>('/api/broker/symbols');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes — matches backend cache TTL
    enabled: isAuthenticated,
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

export function useResetSymbols() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.gateway.post('/api/v1/symbols/reset');
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['symbols'] }),
  });
}
