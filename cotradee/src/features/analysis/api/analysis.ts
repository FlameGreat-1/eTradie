import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';

/**
 * Latest analyses. 60 s safety poll — the realtime WebSocket pushes
 * ANALYSIS_COMPLETE / CYCLE_COMPLETED events that invalidate this
 * key instantly via the realtime provider.
 */
export function useLatestAnalysis(limit = 20) {
  return useQuery({
    queryKey: ['analysis', 'latest', limit],
    queryFn: async () => {
      const { data } = await api.engine.get(`/api/analysis/latest?limit=${limit}`);
      return data;
    },
    refetchInterval: 60_000,
    staleTime: 5_000,
  });
}

export function useAnalysisHistory(params?: {
  since?: string;
  until?: string;
  grade?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: ['analysis', 'history', params],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/analysis/history', { params });
      return data;
    },
  });
}

export function useAnalysisDetail(analysisId: string | null) {
  return useQuery({
    queryKey: ['analysis', 'detail', analysisId],
    queryFn: async () => {
      const { data } = await api.engine.get(`/api/analysis/${analysisId}`);
      return data;
    },
    enabled: !!analysisId,
  });
}

export function useAnalysisStats() {
  return useQuery({
    queryKey: ['analysis', 'stats'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/analysis/stats');
      return data;
    },
    refetchInterval: 60_000,
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
