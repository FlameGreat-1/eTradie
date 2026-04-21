import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export interface SystemConfig {
  enabled: boolean;
  cycle_interval_seconds: number;
  cycle_timeout_seconds: number;
  max_concurrent_symbols: number;
  ta_cache_ttl_seconds: number;
  macro_cache_ttl_seconds: number;
  max_cycle_retries: number;
  default_symbols: string[];
  active_symbols: string[];
  active_symbols_source: string;
  execution_enabled: boolean;
}

export function useSystemConfig() {
  return useQuery({
    queryKey: ['system', 'config'],
    queryFn: async () => {
      const { data } = await api.gateway.get<SystemConfig>('/api/v1/config');
      return data;
    },
  });
}

export function useUpdateInterval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (intervalSeconds: number) => {
      const { data } = await api.gateway.put('/api/v1/config/interval', {
        interval_seconds: intervalSeconds,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['system', 'config'] }),
  });
}
