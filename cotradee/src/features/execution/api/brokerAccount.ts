import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export function useBrokerAccount() {
  return useQuery({
    queryKey: ['execution', 'account'],
    queryFn: async () => {
      const { data } = await api.execution.get('/api/v1/account');
      return data;
    },
    refetchInterval: 5_000,
  });
}

export function useExecutionState() {
  return useQuery({
    queryKey: ['execution', 'state'],
    queryFn: async () => {
      const { data } = await api.execution.get('/api/v1/state');
      return data;
    },
    refetchInterval: 2_000,
  });
}

export function useExecutionSettings() {
  return useQuery({
    queryKey: ['execution', 'settings'],
    queryFn: async () => {
      const { data } = await api.execution.get('/api/v1/settings');
      return data;
    },
  });
}

export function useUpdateExecutionSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (settings: Record<string, unknown>) => {
      const { data } = await api.execution.put('/api/v1/settings', settings);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['execution', 'settings'] }),
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { order_id: string; symbol?: string; reason?: string }) => {
      const { data } = await api.execution.post('/api/v1/orders/cancel', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['execution', 'state'] });
    },
  });
}
