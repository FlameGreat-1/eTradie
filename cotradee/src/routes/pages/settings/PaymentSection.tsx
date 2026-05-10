import { CreditCard, ShieldCheck } from 'lucide-react';

export default function PaymentSection() {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* Payment Methods */}
      <div className="rounded-xl border border-border bg-surface-1 p-6">
        <div className="flex items-center gap-2 mb-4">
          <CreditCard size={16} className="text-brand" />
          <h3 className="text-sm font-semibold text-content">Payment Methods</h3>
        </div>

        <div className="rounded-lg border border-border bg-surface-2 p-8 text-center">
          <CreditCard size={32} className="text-content-muted mx-auto mb-3" />
          <p className="text-sm text-content-muted">
            No payment method on file
          </p>
          <p className="text-xs text-content-muted mt-1">
            Payment methods are managed through our secure payment provider.
          </p>
        </div>
      </div>

      {/* Invoice History */}
      <div className="rounded-xl border border-border bg-surface-1 p-6">
        <h3 className="text-sm font-semibold text-content mb-4">Invoice History</h3>

        <div className="rounded-lg border border-border bg-surface-2 p-8 text-center">
          <p className="text-sm text-content-muted">No invoices yet</p>
          <p className="text-xs text-content-muted mt-1">
            Your billing history will appear here once you subscribe to a plan.
          </p>
        </div>
      </div>

      {/* Security Badge */}
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-4 py-3">
        <ShieldCheck size={14} className="text-success flex-shrink-0" />
        <p className="text-[11px] text-content-muted">
          All payments are processed securely through our verified payment provider with
          HMAC-SHA256 webhook verification. We never store your card details.
        </p>
      </div>
    </div>
  );
}
