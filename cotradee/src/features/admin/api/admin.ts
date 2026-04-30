import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

/* ─── User Management ──────────────────────────── */

export function useAdminUsers() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const { data } = await api.gateway.get('/auth/admin/users');
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useCreateAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { username: string; email: string; password: string; role: string }) => {
      const { data } = await api.gateway.post('/auth/admin/users', payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useActivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.gateway.put(`/auth/admin/users/${userId}/activate`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.gateway.put(`/auth/admin/users/${userId}/deactivate`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

/* ─── Global Processor Config ──────────────────── */

export function useProcessorModels() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['admin', 'processor', 'models'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/processor/models');
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useProcessorConfig() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['admin', 'processor', 'config'],
    queryFn: async () => {
      const { data } = await api.engine.get('/api/processor/config');
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useUpdateProcessorConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (config: Record<string, unknown>) => {
      const { data } = await api.engine.put('/api/processor/config', config);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'processor', 'config'] }),
  });
}
