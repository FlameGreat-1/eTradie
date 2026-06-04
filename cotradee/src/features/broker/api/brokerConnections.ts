import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';
import { toast } from '@/hooks/useToast';

// ---------------------------------------------------------------------------
// Toast helpers
//
// Every mutation on the Broker connections surface now surfaces a
// clear success/error toast. Before this change, the icon-only Test /
// Activate / Delete buttons fired the network call but produced no UI
// signal whatsoever on failure — the user saw nothing move and the
// click 'felt stiff'. The global axios 403 interceptor only renders a
// toast for the structured tier_required envelope; every other 4xx /
// 5xx must be surfaced here.
// ---------------------------------------------------------------------------

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as { detail?: string; error?: string } | undefined;
    if (body?.detail) return body.detail;
    if (body?.error) return body.error;
    if (err.message) return err.message;
  } else if (err instanceof Error) {
    return err.message;
  }
  return fallback;
}

function toastSuccess(title: string, description?: string) {
  toast({ title, description, variant: 'success' });
}

function toastError(title: string, description: string) {
  toast({ title, description, variant: 'destructive' });
}

export function useBrokerConnections() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker', 'connections'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/broker/connections');
      return data.connections ?? [];
    },
    enabled: isAuthenticated,
  });
}

export function useActiveBrokerConnection(options?: any) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker', 'connections', 'active'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/broker/connections/active');
      return data.connection ?? null;
    },
    enabled: isAuthenticated,
    ...options,
  });
}

function invalidateBrokerWorld(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['broker'] });
  qc.invalidateQueries({ queryKey: ['execution'] });
  qc.invalidateQueries({ queryKey: ['management'] });
  qc.invalidateQueries({ queryKey: ['symbols'] });
}

export function useCreateBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.engine.post('/api/broker/connections', payload);
      return data;
    },
    onSuccess: () => {
      invalidateBrokerWorld(qc);
      toastSuccess('Broker connection created', 'Your broker is now linked.');
    },
    onError: (err) => {
      toastError(
        'Create failed',
        errorMessage(err, 'Could not create the broker connection. Try again in a moment.'),
      );
    },
  });
}

export function useUpdateBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: string } & Record<string, unknown>) => {
      const { data } = await api.engine.put(`/api/broker/connections/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      invalidateBrokerWorld(qc);
      toastSuccess('Broker connection updated');
    },
    onError: (err) => {
      toastError(
        'Update failed',
        errorMessage(err, 'Could not update the broker connection. Try again in a moment.'),
      );
    },
  });
}

export function useActivateBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/broker/connections/${id}/activate`);
      return data;
    },
    onSuccess: () => {
      invalidateBrokerWorld(qc);
      toastSuccess('Broker activated');
    },
    onError: (err) => {
      toastError(
        'Activate failed',
        errorMessage(err, 'Could not activate the broker. Try again in a moment.'),
      );
    },
  });
}

// The Test result body. Mirrors what the engine returns from
// POST /api/broker/connections/:id/test. The 'ok' field is the
// canonical success signal; the optional message field carries the
// broker-side diagnostic when ok=false (e.g. 'AUTHORIZED=False',
// 'connection refused', 'symbol mismatch').
type BrokerTestResult = {
  ok?: boolean;
  status?: string;
  message?: string;
  detail?: string;
  account?: Record<string, unknown>;
};

export function useTestBrokerConnection() {
  return useMutation({
    mutationFn: async (id: string): Promise<BrokerTestResult> => {
      const { data } = await api.engine.post<BrokerTestResult>(
        `/api/broker/connections/${id}/test`,
      );
      return data;
    },
    onSuccess: (data) => {
      const ok = data?.ok === true || data?.status === 'ok' || data?.status === 'healthy';
      if (ok) {
        toastSuccess('Connection healthy', 'Broker handshake completed successfully.');
      } else {
        toastError(
          'Connection failed',
          data?.message || data?.detail || 'Broker did not respond as expected.',
        );
      }
    },
    onError: (err) => {
      toastError(
        'Test failed',
        errorMessage(err, 'Could not reach the broker. Check the credentials and try again.'),
      );
    },
  });
}

export function useDeleteBrokerConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.engine.delete(`/api/broker/connections/${id}`);
    },
    onSuccess: () => {
      invalidateBrokerWorld(qc);
      toastSuccess('Broker connection removed');
    },
    onError: (err) => {
      toastError(
        'Delete failed',
        errorMessage(err, 'Could not delete the broker connection. Try again in a moment.'),
      );
    },
  });
}
