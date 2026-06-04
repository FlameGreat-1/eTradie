import { useState } from 'react';
import {
  CreditCard,
  Download,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { useAuth, isAdmin } from '@/features/auth';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { AdminTransactionsPanel } from '@/features/settings/components/AdminTransactionsPanel';
import { useBillingPortal } from '@/features/settings/api/billingPortal';
import {
  formatEventLabel,
  formatExpiry,
  formatMoney,
  isFailedPayment,
  isRefund,
  useUserPaymentHistory,
  useUserPaymentMethod,
  type UserPaymentHistoryRow,
  type UserPaymentMethod,
} from '@/features/settings/api/userBilling';

const PAGE_SIZE = 10;

// Brand display strings. Lower-case keys mirror what the Go parsers
// emit (paddle: card.type, lemonsqueezy: card_brand). Anything not in
// this map falls back to a humanised capitalisation.
const BRAND_LABELS: Record<string, string> = {
  visa: 'Visa',
  mastercard: 'Mastercard',
  amex: 'American Express',
  discover: 'Discover',
  diners: 'Diners Club',
  jcb: 'JCB',
  unionpay: 'UnionPay',
};

function labelForBrand(brand: string): string {
  const key = brand.toLowerCase();
  return BRAND_LABELS[key] ?? brand.charAt(0).toUpperCase() + brand.slice(1);
}

function labelForProvider(provider: string): string {
  if (provider === 'paddle') return 'Paddle';
  if (provider === 'lemonsqueezy') return 'Lemon Squeezy';
  return provider;
}

export default function PaymentSection() {
  const { user } = useAuth();
  const admin = isAdmin(user);

  // Admin width widens for the transactions table; regular users keep
  // the original reading width.
  const wrapClass = admin ? 'space-y-10 w-full max-w-7xl' : 'space-y-10 max-w-2xl';

  return (
    <div className={wrapClass}>
      {/* Payment Methods card is REGULAR-USER ONLY. Admins bypass all
          subscription tier checks (see BillingSection's 'Unrestricted
          Access' card and the backend RequireAdmin middleware), so a
          Payment Methods card on the admin view would either render
          an empty state or leak personal billing context into the
          operator surface. */}
      {!admin && <PaymentMethodsCard />}

      {/* Admin-only: global payment-transactions audit feed. This is
          the canonical admin surface on the Payment page — it
          supersedes both the Payment Methods card and the per-user
          Invoice History feed. */}
      {admin && <AdminTransactionsPanel />}

      {/* Invoice History (regular users only — admins see the global
          AdminTransactionsPanel above which supersedes it). */}
      {!admin && <InvoiceHistoryCard />}

      {/* Security badge — same for everyone. */}
      <div className="flex items-center gap-4 rounded-2xl border border-green-500/20 bg-green-500/5 px-6 py-4 shadow-sm max-w-2xl">
        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center border border-green-500/20">
          <ShieldCheck size={20} className="text-green-500" strokeWidth={2.5} />
        </div>
        <p className="text-[11px] font-bold text-green-600 dark:text-green-400 leading-relaxed uppercase tracking-widest">
          All payments are processed securely through our verified payment provider with
          HMAC-SHA256 webhook verification. We never store your card details.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Payment Methods card
// ---------------------------------------------------------------------------

function PaymentMethodsCard() {
  const { data, isLoading, isError, refetch, isFetching } = useUserPaymentMethod();
  const openPortal = useBillingPortal();

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Methods</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight flex items-center gap-2">
            <CreditCard size={18} className="text-brand" strokeWidth={2.5} />
            Payment Methods
          </h3>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <PaymentMethodsSkeleton />
      ) : isError ? (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <p className="text-sm font-bold text-red-500">Unable to load payment method</p>
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1">
            Try refreshing in a moment.
          </p>
        </div>
      ) : data === null ? (
        <NoPaymentMethodState
          onUpdate={() => openPortal.mutate()}
          portalPending={openPortal.isPending}
        />
      ) : (
        <PaymentMethodPopulated
          method={data as any}
          onUpdate={() => openPortal.mutate()}
          updating={openPortal.isPending}
        />
      )}
    </div>
  );
}

function PaymentMethodsSkeleton() {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-6 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-12 w-16 rounded-lg bg-black/10 dark:bg-white/10" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-32 rounded bg-black/10 dark:bg-white/10" />
          <div className="h-3 w-24 rounded bg-black/10 dark:bg-white/10" />
        </div>
      </div>
    </div>
  );
}

// NoPaymentMethodState renders when /api/v1/billing/payment-method
// returns 204 (no card snapshot stored on billing_subscriptions). The
// CTA must branch on the resolved tier:
//
//   - free        : UpgradeModal (canonical subscribe flow).
//   - pro_byok    : customer portal (already paid; a missing
//                   snapshot is an administrative state, not a
//                   fresh-subscribe gap).
//   - pro_managed : customer portal (same reasoning).
//
// Previously the click unconditionally dispatched 'open-upgrade-modal'.
// That event is consumed by UpgradeModal whose handler short-circuits
// for paying tiers (isTierUnrestricted=true), producing a silent no-op
// that 'felt stiff' from the user's perspective.
function NoPaymentMethodState({
  onUpdate,
  portalPending,
}: {
  onUpdate: () => void;
  portalPending: boolean;
}) {
  const { isProBYOK, isProManaged } = useTierGate();
  const isPaid = isProBYOK || isProManaged;

  const ctaLabel = isPaid
    ? (portalPending ? 'Redirecting…' : 'Update payment method')
    : 'Subscribe to a plan';

  const handleClick = () => {
    if (isPaid) {
      // Paying user with no card snapshot stored — send them to the
      // provider portal so they can add/update payment method. The
      // resulting subscription_* webhook will repopulate the snapshot
      // on billing_subscriptions and the empty state flips to the
      // populated render on the next refetch.
      onUpdate();
      return;
    }
    // Free tier (or any restricted state): canonical upgrade flow.
    window.dispatchEvent(new Event('open-upgrade-modal'));
  };

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-12 text-center shadow-sm">
      <CreditCard size={40} className="text-black/10 dark:text-white/10 mx-auto mb-4" strokeWidth={1.5} />
      <p className="text-sm font-bold text-black dark:text-white tracking-tight">
        No payment method on file
      </p>
      <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1 max-w-[280px] mx-auto leading-relaxed">
        {isPaid
          ? 'You are on a paid plan but no card is currently linked. Update your payment method through our secure provider.'
          : 'Payment methods are added during checkout and managed through our secure payment provider.'}
      </p>
      <button
        type="button"
        onClick={handleClick}
        disabled={isPaid && portalPending}
        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
      >
        {isPaid && <ExternalLink size={12} strokeWidth={3} />}
        {ctaLabel}
      </button>
    </div>
  );
}

function PaymentMethodPopulated({
  method,
  onUpdate,
  updating,
}: {
  method: UserPaymentMethod;
  onUpdate: () => void;
  updating: boolean;
}) {
  const expiry = formatExpiry(method.card_exp_month, method.card_exp_year);
  const brandLabel = labelForBrand(method.card_brand);
  const providerLabel = method.payment_provider
    ? labelForProvider(method.payment_provider)
    : '';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-5 shadow-sm">
        <div className="flex items-center justify-center w-14 h-9 rounded-md border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60">
          {brandLabel.slice(0, 4)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-black dark:text-white tracking-tight">
            {brandLabel} •••• {method.card_last4}
          </p>
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-0.5">
            {expiry ? <>Expires {expiry}</> : null}
            {expiry && providerLabel ? <span className="mx-1.5">•</span> : null}
            {providerLabel ? <>Managed by {providerLabel}</> : null}
          </p>
        </div>
      </div>

      <button
        onClick={onUpdate}
        disabled={updating}
        className="inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-5 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
      >
        <ExternalLink size={14} strokeWidth={3} />
        {updating ? 'Redirecting…' : 'Update payment method'}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invoice History card
// ---------------------------------------------------------------------------

function InvoiceHistoryCard() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch, isFetching } = useUserPaymentHistory(
    page,
    PAGE_SIZE,
  );
  const openPortal = useBillingPortal();

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Accounting</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Invoice History</h3>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <InvoiceHistorySkeleton />
      ) : isError ? (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <p className="text-sm font-bold text-red-500">Unable to load invoice history</p>
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1">
            Try refreshing in a moment.
          </p>
        </div>
      ) : rows.length === 0 ? (
        <NoInvoicesState />
      ) : (
        <>
          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black overflow-x-auto shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="text-[10px] uppercase tracking-widest text-black/30 dark:text-white/30 bg-black/[0.02] dark:bg-white/[0.02]">
                <tr>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Description</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-left">Card</th>
                  <th className="px-4 py-3 text-right">Invoice</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <InvoiceRow
                    key={row.id}
                    row={row}
                    onOpenPortal={() => openPortal.mutate()}
                    portalPending={openPortal.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-xs text-black/40 dark:text-white/40">
              <span>
                Page {data?.page ?? 1} of {totalPages} — {total} invoices
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function InvoiceHistorySkeleton() {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-6 animate-pulse space-y-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex items-center gap-4">
          <div className="h-3 w-24 rounded bg-black/10 dark:bg-white/10" />
          <div className="h-3 flex-1 rounded bg-black/10 dark:bg-white/10" />
          <div className="h-3 w-16 rounded bg-black/10 dark:bg-white/10" />
        </div>
      ))}
    </div>
  );
}

function NoInvoicesState() {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-12 text-center shadow-sm">
      <p className="text-sm font-bold text-black dark:text-white tracking-tight">No invoices yet</p>
      <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1 max-w-[240px] mx-auto leading-relaxed">
        Your billing history will appear here once you subscribe to a plan.
      </p>
    </div>
  );
}

function InvoiceRow({
  row,
  onOpenPortal,
  portalPending,
}: {
  row: UserPaymentHistoryRow;
  onOpenPortal: () => void;
  portalPending: boolean;
}) {
  const refund = isRefund(row.event_name);
  const failed = isFailedPayment(row.event_name);

  const amountClass = refund
    ? 'text-yellow-600 dark:text-yellow-400'
    : failed
      ? 'text-red-500'
      : 'text-black dark:text-white';

  const amountText = formatMoney(row.amount_cents, row.currency);
  const amountDisplay = refund && amountText !== '—' ? `-${amountText}` : amountText;

  const labelText = formatEventLabel(row.event_name);
  const labelBadgeClass = failed
    ? 'bg-red-500/10 text-red-500 border-red-500/20'
    : refund
      ? 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20'
      : 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20';

  const ts = new Date(row.event_timestamp);
  const dateText = ts.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  const cardText =
    row.card_brand && row.card_last4
      ? `${labelForBrand(row.card_brand)} •••• ${row.card_last4}`
      : null;

  return (
    <tr className="border-t border-black/5 dark:border-white/5 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
      <td className="px-4 py-3 text-black/60 dark:text-white/60 whitespace-nowrap text-xs">
        {dateText}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${labelBadgeClass}`}
        >
          {labelText}
        </span>
      </td>
      <td className={`px-4 py-3 text-right tabular-nums font-bold ${amountClass}`}>
        {amountDisplay}
      </td>
      <td className="px-4 py-3 text-black/60 dark:text-white/60 text-xs">
        {cardText ?? '—'}
      </td>
      <td className="px-4 py-3 text-right">
        {row.invoice_url ? (
          <a
            href={row.invoice_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-brand hover:opacity-80 transition-opacity"
          >
            <Download size={12} strokeWidth={3} />
            PDF
          </a>
        ) : (
          <button
            onClick={onOpenPortal}
            disabled={portalPending}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-colors disabled:opacity-40"
            title="Open customer portal to download invoice"
          >
            <ExternalLink size={12} strokeWidth={3} />
            Portal
          </button>
        )}
      </td>
    </tr>
  );
}
