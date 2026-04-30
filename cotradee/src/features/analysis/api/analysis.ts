import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { POLL_RETRY, adaptiveInterval } from '@/lib/queryHelpers';
import { useAuth } from '@/features/auth/context/AuthContext';

/**
 * Latest analyses. 60 s safety poll — the realtime WebSocket pushes
 * ANALYSIS_COMPLETE / CYCLE_COMPLETED events that invalidate this
 * key instantly via the realtime provider.
 */
export function useLatestAnalysis(limit = 20) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['analysis', 'latest', limit],
    queryFn: async () => {
      const { data } = await api.engine.get(`/api/analysis/latest?limit=${limit}`);
      return data;
    },
    refetchInterval: adaptiveInterval(60_000),
    staleTime: 5_000,
    retry: POLL_RETRY,
    enabled: isAuthenticated,
  });
}

export function useAnalysisHistory(params?: {
  since?: string;
  until?: string;
  grade?: string;
  status?: string;
}) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['analysis', 'history', params],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/analysis/history', { params });
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useAnalysisDetail(analysisId: string | null) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['analysis', 'detail', analysisId],
    queryFn: async () => {
      const { data } = await api.engine.get(`/api/analysis/${analysisId}`);
      return data;
    },
    enabled: !!analysisId && isAuthenticated,
  });
}

export function useAnalysisStats() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['analysis', 'stats'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/analysis/stats');
      return data;
    },
    refetchInterval: adaptiveInterval(60_000),
    retry: POLL_RETRY,
    enabled: isAuthenticated,
  });
}

export function useRerunAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (symbol?: string) => {
      const { data } = await api.engine.post('/api/analysis/rerun', null, {
        params: symbol ? { symbol } : undefined,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analysis'] }),
  });
}

export function useRunCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (symbols?: string[]) => {
      const { data } = await api.gateway.post('/api/v1/cycle/run', {
        symbols: symbols || [],
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analysis'] }),
  });
}
