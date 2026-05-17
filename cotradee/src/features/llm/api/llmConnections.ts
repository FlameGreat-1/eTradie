import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';
import { toast } from '@/hooks/useToast';

// ---------------------------------------------------------------------------
// Toast helpers
//
// Every mutation on the LLM connections surface now surfaces a clear
// success/error toast. Before this change, the icon-only Activate /
// Deactivate / Delete / Test buttons fired the network call but
// produced no UI signal whatsoever on failure — the user saw nothing
// move and the click 'felt stiff'. The global axios 403 interceptor
// only renders a toast for the structured tier_required envelope;
// every other 4xx / 5xx must be surfaced here.
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

export function useLlmProviders() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['llm', 'providers'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/llm/providers');
      return data;
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('API key connected', 'Your provider key is active.');
    },
    onError: (err) => {
      toastError(
        'Connection failed',
        errorMessage(err, 'Could not save the API key. Try again in a moment.'),
      );
    },
  });
}

export function useUpdateLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: string } & Record<string, unknown>) => {
      const { data } = await api.engine.put(`/api/llm/connections/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm', 'connections'] });
      toastSuccess('Connection updated');
    },
    onError: (err) => {
      toastError(
        'Update failed',
        errorMessage(err, 'Could not update the connection. Try again in a moment.'),
      );
    },
  });
}

export function useActivateLlm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/llm/connections/${id}/activate`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('Connection activated');
    },
    onError: (err) => {
      toastError(
        'Activate failed',
        errorMessage(err, 'Could not activate the connection. Try again in a moment.'),
      );
    },
  });
}

export function useDeactivateLlm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.engine.post(`/api/llm/connections/${id}/deactivate`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('Connection deactivated');
    },
    onError: (err) => {
      toastError(
        'Deactivate failed',
        errorMessage(err, 'Could not deactivate the connection. Try again in a moment.'),
      );
    },
  });
}

export function useDeleteLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.engine.delete(`/api/llm/connections/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('Connection removed');
    },
    onError: (err) => {
      toastError(
        'Delete failed',
        errorMessage(err, 'Could not delete the connection. Try again in a moment.'),
      );
    },
  });
}

// -- Platform Admin Hooks ---------------------------------------------------

export function usePlatformLlmConnection() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['llm', 'platform', 'connection'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/llm/platform/connection');
      return data.connection ?? null;
    },
    enabled: isAuthenticated,
  });
}

export function useSetPlatformLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.engine.post('/api/llm/platform/connection', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('Platform key saved', 'The system will now use this key.');
    },
    onError: (err) => {
      toastError(
        'Save failed',
        errorMessage(err, 'Could not save the platform key. Try again.'),
      );
    },
  });
}

export function useDeletePlatformLlmConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.engine.delete('/api/llm/platform/connection');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm'] });
      toastSuccess('Platform key removed', 'Reverted to .env fallback.');
    },
    onError: (err) => {
      toastError(
        'Delete failed',
        errorMessage(err, 'Could not delete the platform key. Try again.'),
      );
    },
  });
}
