import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

export function useLlmProviders() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['llm', 'providers'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/llm/providers');
      return data.providers;
    },
    enabled: isAuthenticated,
  });
}

export function useLlmConnections() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['llm', 'connections'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/llm/connections');
      return data.connections ?? [];
    },
    enabled: isAuthenticated,
  });
}

export function useActiveLlmConnection() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['llm', 'connections', 'active'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/llm/connections/active');
      return data.connection ?? null;
    },
    enabled: isAuthenticated,
  });
}

export function useCreateLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.engine.post('/api/llm/connections', payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm', 'connections'] }),
  });
}

export function useUpdateLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: string } & Record<string, unknown>) => {
      const { data } = await api.engine.put(`/api/llm/connections/${id}`, payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm', 'connections'] }),
  });
}

export function useActivateLlm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/llm/connections/${id}/activate`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm'] }),
  });
}

export function useDeactivateLlm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/llm/connections/${id}/deactivate`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm'] }),
  });
}

export function useDeleteLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.engine.delete(`/api/llm/connections/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm', 'connections'] }),
  });
}
