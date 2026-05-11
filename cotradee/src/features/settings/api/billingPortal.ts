import { useMutation } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { api } from '@/lib/axios';
import { useToast } from '@/hooks/useToast';

interface PortalResponse {
  portal_url: string;
}

/**
 * useBillingPortal opens the active subscription's customer-portal
 * session on the original payment provider (Paddle or Lemon Squeezy).
 *
 * Behaviour:
 *   - On success, the browser is redirected to the portal URL so the
 *     user can update card, cancel, change plan, or download invoices
 *     against the SAME provider that originally took the payment.
 *   - On 404 (no active subscription) the caller can fall back to the
 *     upgrade flow; we surface a toast so the user understands why.
 *   - On any other error a destructive toast renders the server-side
 *     reason verbatim (the gateway returns 'billing service
 *     unavailable', 'portal not supported by provider', etc.).
 *
 * The endpoint is POST so it is CSRF-protected by the gateway's
 * RequireCSRF middleware. Provider API keys never leave the billing
 * microservice; the gateway proxies the request behind the internal
 * shared secret.
 */
export function useBillingPortal() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: async () => {
      const { data } = await api.gateway.post<PortalResponse>(
        '/api/v1/billing/portal',
      );
      if (!data.portal_url) {
        throw new Error('Billing service returned an empty portal URL.');
      }
      return data.portal_url;
    },
    onSuccess: (portalUrl) => {
      window.location.href = portalUrl;
    },
    onError: (err) => {
      let message = 'Unable to open the billing portal.';
      let isMissingSub = false;
      if (err instanceof AxiosError) {
        const status = err.response?.status;
        const body = err.response?.data as { error?: string } | undefined;
        if (status === 404) {
          isMissingSub = true;
          message =
            'You do not have an active subscription yet. Start one from the Upgrade flow.';
        } else if (body?.error) {
          message = body.error;
        } else if (err.message) {
          message = err.message;
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      toast({
        title: isMissingSub ? 'No active subscription' : 'Billing portal unavailable',
        description: message,
        variant: isMissingSub ? 'warning' : 'destructive',
      });
    },
  });
}
