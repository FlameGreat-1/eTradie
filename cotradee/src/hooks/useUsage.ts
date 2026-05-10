import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export interface UsageData {
  tier: string;
  analyses_today: number;
  last_analysis_at: string | null;
  last_reset_at: string | null;
  daily_limit: number | null;
  ta_cycles_used: number;
  macro_cycles_used: number;
  execution_attempts: number;
}

export function useUsage() {
  return useQuery<UsageData>({
    queryKey: ['usage', 'me'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/usage/me');
      return data;
    },
    refetchInterval: 60_000, // Refresh every 60s to keep countdown accurate.
    staleTime: 30_000,
  });
}
