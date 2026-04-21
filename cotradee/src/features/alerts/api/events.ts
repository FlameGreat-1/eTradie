import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

export function useRecentEvents(count = 50, severity?: string) {
  return useQuery({
    queryKey: ['events', 'recent', { count, severity }],
    queryFn: async () => {
      const params: Record<string, string> = { count: count.toString() };
      if (severity) params.severity = severity;
      const { data } = await api.gateway.get('/events/recent', { params });
      return data.events;
    },
    refetchInterval: 10_000,
  });
}

export function useEventsSince(lastEventId: string | null, count = 100) {
  return useQuery({
    queryKey: ['events', 'since', lastEventId],
    queryFn: async () => {
      const params: Record<string, string> = { count: count.toString() };
      if (lastEventId) params.last_event_id = lastEventId;
      const { data } = await api.gateway.get('/events/since', { params });
      return data.events;
    },
    enabled: !!lastEventId,
  });
}
