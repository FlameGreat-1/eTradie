import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export function useBrokerConnections() {
  return useQuery({
    queryKey: ['broker', 'connections'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/broker/connections');
      return data.connections ?? [];
    },
  });
}

export function useActiveBrokerConnection() {
  return useQuery({
    queryKey: ['broker', 'connections', 'active'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/broker/connections/active');
      return data.connection ?? null;
    },
  });
}

export function useCreateBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.engine.post('/api/broker/connections', payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broker', 'connections'] }),
  });
}

export function useUpdateBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: string } & Record<string, unknown>) => {
      const { data } = await api.engine.put(`/api/broker/connections/${id}`, payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broker', 'connections'] }),
  });
}

export function useActivateBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/broker/connections/${id}/activate`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broker'] }),
  });
}

export function useTestBrokerConnection() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/broker/connections/${id}/test`);
      return data;
    },
  });
}

export function useDeleteBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.engine.delete(`/api/broker/connections/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broker', 'connections'] }),
  });
}
