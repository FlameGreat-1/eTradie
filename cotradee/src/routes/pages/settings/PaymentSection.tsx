import { CreditCard, ShieldCheck } from 'lucide-react';
import { useAuth, isAdmin } from '@/features/auth';
import { AdminTransactionsPanel } from '@/features/settings/components/AdminTransactionsPanel';

export default function PaymentSection() {
  const { user } = useAuth();
  const admin = isAdmin(user);

  // The container width widens for admins so the transactions table
  // has room; regular users keep the original reading width.
  const wrapClass = admin ? 'space-y-10 w-full max-w-7xl' : 'space-y-10 max-w-2xl';

  return (
    <div className={wrapClass}>
      {/* Payment Methods — same for everyone */}
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm max-w-2xl">
        <div className="flex flex-col gap-0.5 mb-6">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Methods</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight flex items-center gap-2">
            <CreditCard size={18} className="text-brand" strokeWidth={2.5} />
            Payment Methods
          </h3>
        </div>

        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-12 text-center shadow-sm">
          <CreditCard size={40} className="text-black/10 dark:text-white/10 mx-auto mb-4" strokeWidth={1.5} />
          <p className="text-sm font-bold text-black dark:text-white tracking-tight">
            No payment method on file
          </p>
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1 max-w-[240px] mx-auto leading-relaxed">
            Payment methods are managed through our secure payment provider.
          </p>
        </div>
      </div>

      {/* Admin-only: global payment-transactions audit feed.
          Regular users never reach this branch; they see the Invoice
          History placeholder below instead. */}
      {admin && <AdminTransactionsPanel />}

      {/* Invoice History — regular users only. For admins this is
          superseded by the AdminTransactionsPanel above. */}
      {!admin && (
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm max-w-2xl">
          <div className="flex flex-col gap-0.5 mb-6">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Accounting</div>
            <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Invoice History</h3>
          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-black p-12 text-center shadow-sm">
            <p className="text-sm font-bold text-black dark:text-white tracking-tight">No invoices yet</p>
            <p className="text-[11px] font-medium text-black/40 dark:text-white/40 mt-1 max-w-[240px] mx-auto leading-relaxed">
              Your billing history will appear here once you subscribe to a plan.
            </p>
          </div>
        </div>
      )}

      {/* Security Badge — same for everyone */}
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
