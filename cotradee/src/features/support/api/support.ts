import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { gatewayApi } from '@/lib/axios';
import { useAuth } from '@/features/auth';
import { POLL_RETRY, adaptiveInterval } from '@/lib/queryHelpers';
import { toast } from '@/hooks/useToast';
import type {
  AppendMessageResponse,
  CommunityLinksResponse,
  ContactFormInput,
  NewTicketInput,
  ReplyInput,
  Ticket,
  TicketListResponse,
  TicketResponse,
} from '../types';

/**
 * React Query keys for the support feature. Centralising them here
 * lets every component reach the same cache entry and prevents typos
 * from silently splitting the cache. The tuple format is the convention
 * used by features/alerts and features/auth.
 */
export const supportKeys = {
  all: ['support'] as const,
  community: () => [...supportKeys.all, 'community'] as const,
  tickets: () => [...supportKeys.all, 'tickets'] as const,
  ticketList: (args: { limit: number; offset: number }) =>
    [...supportKeys.tickets(), 'list', args] as const,
  ticket: (id: string) => [...supportKeys.tickets(), 'detail', id] as const,
} as const;

/** Convert any axios error to a human-readable string for toasts. */
function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as { error?: string } | undefined;
    if (data?.error) return data.error;
    if (err.message) return err.message;
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// PUBLIC: community links
// ---------------------------------------------------------------------------

/**
 * Fetch the configured Facebook/Discord/Telegram/WhatsApp links.
 * Endpoint is unauthenticated, so the hook does not gate on auth
 * state — the landing page calls it directly.
 */
export function useCommunityLinks() {
  return useQuery<CommunityLinksResponse>({
    queryKey: supportKeys.community(),
    queryFn: async () => {
      const { data } = await gatewayApi.get<CommunityLinksResponse>('/api/support/community-links');
      return data;
    },
    // Community links are essentially static config; keep the data
    // in cache for 10 minutes between refetches.
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

// ---------------------------------------------------------------------------
// PUBLIC: contact form
// ---------------------------------------------------------------------------

/** Submit the unauthenticated /api/support/contact form. */
export async function submitContact(input: ContactFormInput): Promise<Ticket> {
  const { data } = await gatewayApi.post<TicketResponse>('/api/support/contact', input);
  return data.ticket;
}

export function useSubmitContact() {
  return useMutation({
    mutationFn: submitContact,
    onError: (err) => {
      toast({
        title: 'Could not send your message',
        description: errorMessage(err, 'Please try again in a moment.'),
        variant: 'destructive',
      });
    },
  });
}

// ---------------------------------------------------------------------------
// AUTHENTICATED: list / get / create / reply / close
// ---------------------------------------------------------------------------

export interface UseMyTicketsOptions {
  limit?: number;
  offset?: number;
}

export function useMyTickets(opts: UseMyTicketsOptions = {}) {
  const { isAuthenticated } = useAuth();
  const limit = opts.limit ?? 25;
  const offset = opts.offset ?? 0;
  return useQuery<TicketListResponse>({
    queryKey: supportKeys.ticketList({ limit, offset }),
    queryFn: async () => {
      const { data } = await gatewayApi.get<TicketListResponse>('/api/support/tickets', {
        params: { limit, offset },
      });
      return data;
    },
    enabled: isAuthenticated,
    refetchInterval: adaptiveInterval(30_000),
    retry: POLL_RETRY,
  });
}

export function useTicket(ticketId: string | null | undefined) {
  const { isAuthenticated } = useAuth();
  return useQuery<Ticket>({
    queryKey: ticketId ? supportKeys.ticket(ticketId) : ['support', 'tickets', 'detail', 'none'],
    queryFn: async () => {
      const { data } = await gatewayApi.get<TicketResponse>(`/api/support/tickets/${ticketId}`);
      return data.ticket;
    },
    enabled: isAuthenticated && !!ticketId,
    refetchInterval: adaptiveInterval(15_000),
    retry: POLL_RETRY,
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: NewTicketInput): Promise<Ticket> => {
      const { data } = await gatewayApi.post<TicketResponse>('/api/support/tickets', input);
      return data.ticket;
    },
    onSuccess: (ticket) => {
      qc.invalidateQueries({ queryKey: supportKeys.tickets() });
      qc.setQueryData(supportKeys.ticket(ticket.id), ticket);
      toast({
        title: 'Ticket opened',
        description: `Reference: ${ticket.public_ref}`,
      });
    },
    onError: (err) => {
      toast({
        title: 'Could not open ticket',
        description: errorMessage(err, 'Please try again in a moment.'),
        variant: 'destructive',
      });
    },
  });
}

export interface ReplyMutationVars {
  ticketId: string;
  input: ReplyInput;
}

export function useReplyToTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ticketId, input }: ReplyMutationVars): Promise<AppendMessageResponse> => {
      const { data } = await gatewayApi.post<AppendMessageResponse>(
        `/api/support/tickets/${ticketId}/messages`,
        input,
      );
      return data;
    },
    onSuccess: (_resp, vars) => {
      qc.invalidateQueries({ queryKey: supportKeys.ticket(vars.ticketId) });
      qc.invalidateQueries({ queryKey: supportKeys.tickets() });
    },
    onError: (err) => {
      toast({
        title: 'Could not send reply',
        description: errorMessage(err, 'Please try again in a moment.'),
        variant: 'destructive',
      });
    },
  });
}

export function useCloseTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ticketId: string): Promise<Ticket> => {
      const { data } = await gatewayApi.post<TicketResponse>(
        `/api/support/tickets/${ticketId}/close`,
      );
      return data.ticket;
    },
    onSuccess: (ticket) => {
      qc.setQueryData(supportKeys.ticket(ticket.id), ticket);
      qc.invalidateQueries({ queryKey: supportKeys.tickets() });
      toast({
        title: 'Ticket closed',
        description: `Reference: ${ticket.public_ref}`,
      });
    },
    onError: (err) => {
      toast({
        title: 'Could not close ticket',
        description: errorMessage(err, 'Please try again in a moment.'),
        variant: 'destructive',
      });
    },
  });
}
