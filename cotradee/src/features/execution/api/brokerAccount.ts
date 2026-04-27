import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';

/**
 * Live broker account snapshot. Refetches every 5 s as a safety net;
 * the realtime WebSocket pushes the authoritative delta whenever
 * money moves on the account (ORDER_FILLED, TRADE_CLOSED,
 * PARTIAL_CLOSE, BROKER_DISCONNECTED, BROKER_RECONNECTED).
 */
export function useBrokerAccount() {
  return useQuery({
    queryKey: ['execution', 'account'],
    queryFn: async () => {
      const { data } = await api.execution.get('/api/v1/account');
      return data;
    },
    refetchInterval: 5_000,
    staleTime: 1_000,
  });
}

/**
 * Live execution state: open positions and pending orders.
 * Polled every 3 s; WS events for order lifecycle invalidate this
 * key instantly via the realtime provider.
 */
export function useExecutionState() {
  return useQuery({
    queryKey: ['execution', 'state'],
    queryFn: async () => {
      const { data } = await api.execution.get('/api/v1/state');
      return data;
    },
    refetchInterval: 3_000,
    staleTime: 500,
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
