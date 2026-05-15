import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

// ---------------------------------------------------------------------------
// Response shapes (mirror Go billingstore.UserPaymentMethod /
// UserPaymentHistoryRow exactly).
// ---------------------------------------------------------------------------

export interface UserPaymentMethod {
  card_brand: string;
  card_last4: string;
  card_exp_month: number;
  card_exp_year: number;
  payment_provider: string;
  provider_customer_id: string;
}

export interface UserPaymentHistoryRow {
  id: number;
  provider: string;
  event_name: string;
  event_timestamp: string; // ISO-8601
  created_at: string; // ISO-8601
  amount_cents: number | null;
  currency: string | null;
  invoice_url: string | null;
  card_brand: string | null;
  card_last4: string | null;
}

export interface PaginatedUserPaymentHistory {
  rows: UserPaymentHistoryRow[];
  total: number;
  page: number;
  size: number;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * useUserPaymentMethod returns the authenticated user's latest card
 * snapshot. data === null is the canonical signal that the user has
 * never paid (backend returns 204 No Content in that case); component
 * code should branch on the null and render the 'no payment method on
 * file' empty state.
 *
 * staleTime is 30s: the payment method changes only through the
 * provider's customer portal, which is a low-frequency operation. A
 * refresh button on the SPA invalidates this query immediately.
 */
export function useUserPaymentMethod() {
  return useQuery<UserPaymentMethod | null>({
    queryKey: ['billing', 'user', 'payment-method'],
    queryFn: async () => {
      const resp = await api.gateway.get<UserPaymentMethod>(
        '/api/v1/billing/payment-method',
      );
      // 204 No Content -> axios resolves with status=204 and data='' (or
      // undefined depending on transformResponse). Normalise to null so
      // consumers have a single sentinel for 'no method on file'.
      if (resp.status === 204) return null;
      return resp.data ?? null;
    },
    staleTime: 30_000,
  });
}

/**
 * useUserPaymentHistory returns one page of the user's own financial
 * events newest-first. Server clamps page size at 100; passing larger
 * values is harmless (the response echoes the effective size).
 *
 * staleTime is 15s: financial events arrive via webhook so the feed
 * can change at any time, but polling more often than 15s would be
 * pointless for what is a low-update-rate stream in practice.
 */
export function useUserPaymentHistory(page: number, size: number) {
  return useQuery<PaginatedUserPaymentHistory>({
    queryKey: ['billing', 'user', 'transactions', page, size],
    queryFn: async () => {
      const sp = new URLSearchParams();
      sp.set('page', String(page));
      sp.set('size', String(size));
      const { data } = await api.gateway.get<PaginatedUserPaymentHistory>(
        `/api/v1/billing/transactions?${sp.toString()}`,
      );
      return data;
    },
    staleTime: 15_000,
  });
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

/**
 * formatMoney renders an integer-minor-units amount and ISO-4217
 * currency code into a human-readable string. Falls back to a neutral
 * dash when either input is null — callers pass the row's nullable
 * pointers straight through without their own guard.
 *
 * Uses Intl.NumberFormat with `style: 'currency'` so the result is
 * locale-correct (en-GB shows £9.99, fr-FR shows 9,99 €, etc.). The
 * locale falls through to the browser's default, matching the rest
 * of the dashboard's i18n posture.
 */
export function formatMoney(
  amountCents: number | null,
  currency: string | null,
): string {
  if (amountCents === null || currency === null) return '—';
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
    }).format(amountCents / 100);
  } catch {
    // Unknown ISO code (theoretically impossible with provider data,
    // but Intl throws RangeError on bad inputs). Fall back to a plain
    // string so the UI never crashes on a single bad row.
    return `${(amountCents / 100).toFixed(2)} ${currency}`;
  }
}

/**
 * formatExpiry renders 'MM/YYYY' for a card expiry. Returns null when
 * either component is missing so the calling component can omit the
 * cell entirely.
 */
export function formatExpiry(month: number, year: number): string | null {
  if (!month || !year) return null;
  const mm = String(month).padStart(2, '0');
  return `${mm}/${year}`;
}

/**
 * Display copy for each financial event_name. Centralised so the SPA
 * does not branch on raw provider strings inside JSX. Unknown names
 * fall back to a humanised version of the underscored string.
 */
const EVENT_LABELS: Record<string, string> = {
  transaction_completed: 'Payment',
  subscription_payment_success: 'Payment',
  subscription_payment_failed: 'Payment failed',
  subscription_payment_refunded: 'Refund',
};

export function formatEventLabel(eventName: string): string {
  return (
    EVENT_LABELS[eventName] ??
    eventName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/**
 * isRefund returns true for events that represent money moving BACK
 * to the customer. Drives the negative-amount + amber colour styling
 * on the Invoice History rows.
 */
export function isRefund(eventName: string): boolean {
  return eventName === 'subscription_payment_refunded';
}

/**
 * isFailedPayment returns true for events that represent a failed
 * charge. Drives the destructive (red) styling on the row and the
 * 'past due' badge.
 */
export function isFailedPayment(eventName: string): boolean {
  return eventName === 'subscription_payment_failed';
}
