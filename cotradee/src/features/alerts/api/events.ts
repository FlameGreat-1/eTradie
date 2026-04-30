import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { POLL_RETRY, adaptiveInterval } from '@/lib/queryHelpers';
import { useAuth } from '@/features/auth/context/AuthContext';

export function useRecentEvents(count = 50, severity?: string) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['events', 'recent', { count, severity }],
    queryFn: async () => {
      const params: Record<string, string> = { count: count.toString() };
      if (severity) params.severity = severity;
      const { data } = await api.gateway.get('/events/recent', { params });
      return data.events;
    },
    refetchInterval: adaptiveInterval(10_000),
    retry: POLL_RETRY,
    enabled: isAuthenticated,
  });
}

export function useEventsSince(lastEventId: string | null, count = 100) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['events', 'since', lastEventId],
    queryFn: async () => {
      const params: Record<string, string> = { count: count.toString() };
      if (lastEventId) params.last_event_id = lastEventId;
      const { data } = await api.gateway.get('/events/since', { params });
      return data.events;
    },
    enabled: !!lastEventId && isAuthenticated,
  });
}
