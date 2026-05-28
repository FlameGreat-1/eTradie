/**
 * AdminQuotaPolicyPanel
 *
 * Admin-only panel that edits the platform-managed LLM quota policy
 * stored in tier_quota_policies (migration 0028). One editable card
 * per ENFORCED tier (pro_managed + admin). BYOK tiers (free,
 * pro_byok) are NOT rendered here because, per the product decision
 * captured in QUOTA.md, those users supply their own provider key
 * and the platform never debits a reservation on their behalf;
 * showing zero-value cards for them would look like a
 * misconfiguration.
 *
 * Layout, iconography, and form ergonomics intentionally mirror
 * AdminProcessorConfigPanel.tsx so the Settings page reads as one
 * coherent admin surface.
 *
 * Validation client-side MIRRORS billingstore.ValidatePolicy on the
 * Go side -- same ranges, same enforced-requires-non-zero-caps rule,
 * same allowed_models normalisation. The server is still authoritative
 * (defense-in-depth); a client-side bypass surfaces as a 400 with
 * the server's exact message.
 *
 * Audit ref: ADMIN-QUOTA-12.
 */
import { useEffect, useMemo, useState } from 'react';
import { Gauge, RefreshCw, Save } from 'lucide-react';
import {
  useAdminQuotaPolicies,
  useUpdateAdminQuotaPolicy,
  type QuotaPolicyRow,
} from '../api/quota';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Tiers we render as editable cards. MUST match the Enforced=true
 * rows in the 0028 seed. Free / pro_byok are intentionally absent
 * because they are BYOK by design.
 */
const EDITABLE_TIERS = ['pro_managed', 'admin'] as const;
type EditableTier = (typeof EDITABLE_TIERS)[number];

/**
 * Per-field validation bounds. MUST match billingstore.ValidatePolicy
 * AND the migration's CHECK constraints. Drift in any of the three
 * layers produces a confusing "why did my value not save" UX.
 */
const BOUNDS = {
  daily_input_tokens:        { min: 0, label: 'Daily input tokens' },
  daily_output_tokens:       { min: 0, label: 'Daily output tokens' },
  monthly_input_tokens:      { min: 0, label: 'Monthly input tokens' },
  monthly_output_tokens:     { min: 0, label: 'Monthly output tokens' },
  max_input_tokens_per_call: { min: 0, label: 'Max input tokens per call' },
  soft_cap_percent:          { min: 0, max: 100,  label: 'Soft cap percent' },
  reservation_ttl_seconds:   { min: 30, max: 3600, label: 'Reservation TTL (seconds)' },
} as const;

// ---------------------------------------------------------------------------
// Pure helpers (exported-by-shape for unit-test parity with Go validator)
// ---------------------------------------------------------------------------

/** Normalise allowed_models text input to the same shape ValidatePolicy enforces. */
function normaliseAllowedModels(text: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of text.split(',')) {
    const m = raw.trim().toLowerCase();
    if (m === '' || seen.has(m)) continue;
    seen.add(m);
    out.push(m);
  }
  return out;
}

/**
 * Client-side mirror of billingstore.ValidatePolicy. Returns null on
 * success or the first failing field's message verbatim.
 */
function validateRow(r: QuotaPolicyRow): string | null {
  for (const [k, b] of Object.entries(BOUNDS)) {
    const v = (r as unknown as Record<string, number>)[k];
    if (!Number.isFinite(v)) return `${b.label} must be a finite number`;
    if (v < b.min) return `${b.label} must be >= ${b.min}`;
    if ('max' in b && v > b.max) return `${b.label} must be <= ${b.max}`;
  }
  if (r.enforced) {
    if (
      r.daily_input_tokens === 0 ||
      r.daily_output_tokens === 0 ||
      r.monthly_input_tokens === 0 ||
      r.monthly_output_tokens === 0 ||
      r.max_input_tokens_per_call === 0
    ) {
      return 'Enforced policy requires all four token caps and max-per-call to be greater than zero';
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AdminQuotaPolicyPanel() {
  const listQuery = useAdminQuotaPolicies();
  const updateMutation = useUpdateAdminQuotaPolicy();

  if (listQuery.isLoading) {
    return (
      <div className="p-8 text-center text-sm text-content-muted">
        Loading quota policies...
      </div>
    );
  }

  if (listQuery.isError) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-sm text-red-500">
        Failed to load quota policies. Refresh to retry.
      </div>
    );
  }

  const rows = listQuery.data?.rows ?? [];
  const editable = rows.filter((r) =>
    (EDITABLE_TIERS as readonly string[]).includes(r.tier as string),
  );

  return (
    <div className="rounded-2xl border border-brand/20 bg-brand/5 p-6 shadow-sm mb-10 max-w-3xl">
      <div className="flex items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 rounded-xl bg-brand/10 p-2 border border-brand/20 shadow-sm">
            <Gauge size={16} className="text-brand" strokeWidth={2.5} />
          </div>
          <div className="space-y-1">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-brand mb-1">
              Platform LLM Quota
            </h3>
            <p className="text-sm font-bold text-black dark:text-white tracking-tight">
              Tier Quota Policies
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => listQuery.refetch()}
          disabled={listQuery.isFetching}
          className="rounded-xl bg-black dark:bg-white px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-sm transition-all disabled:opacity-40 flex items-center gap-2"
        >
          <RefreshCw
            size={12}
            strokeWidth={3}
            className={listQuery.isFetching ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      <p className="mt-6 mb-6 text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
        Caps below apply ONLY to users on the platform-managed AI key
        (Pro Managed tier and Admins). Free and Pro BYOK tiers supply
        their own provider keys and are not metered by the platform,
        so they have no editable policy here by design.
      </p>

      {editable.length === 0 ? (
        <div className="text-sm text-content-muted">
          No enforced tier rows found. Run the 0028 seed migration.
        </div>
      ) : (
        <div className="space-y-6">
          {editable.map((row) => (
            <TierCard
              key={row.tier}
              initial={row}
              onSave={(next) =>
                updateMutation.mutateAsync({ tier: row.tier, row: next })
              }
              saving={
                updateMutation.isPending &&
                updateMutation.variables?.tier === row.tier
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single-tier card
// ---------------------------------------------------------------------------

function TierCard({
  initial,
  onSave,
  saving,
}: {
  initial: QuotaPolicyRow;
  onSave: (row: QuotaPolicyRow) => Promise<QuotaPolicyRow>;
  saving: boolean;
}) {
  const [form, setForm] = useState<QuotaPolicyRow>(initial);
  const [allowedText, setAllowedText] = useState<string>(
    (initial.allowed_models ?? []).join(', '),
  );
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);

  // Re-sync form when the server row changes (post-mutation refetch).
  useEffect(() => {
    setForm(initial);
    setAllowedText((initial.allowed_models ?? []).join(', '));
  }, [initial]);

  const tierLabel = useMemo(() => labelFor(initial.tier as EditableTier), [initial.tier]);

  const handleNumber = (field: keyof QuotaPolicyRow) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    setForm((prev) => ({ ...prev, [field]: Number.isFinite(v) ? v : 0 }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    const next: QuotaPolicyRow = {
      ...form,
      tier: initial.tier,
      allowed_models: normaliseAllowedModels(allowedText),
    };

    const clientErr = validateRow(next);
    if (clientErr) {
      setMessage({ kind: 'error', text: clientErr });
      return;
    }

    try {
      await onSave(next);
      setMessage({
        kind: 'success',
        text: 'Policy saved. The metering layer will pick up the new caps on the next request.',
      });
    } catch (err) {
      const errObj = err as { response?: { data?: { error?: string } } };
      const serverMsg =
        errObj?.response?.data?.error ||
        'Failed to save quota policy. Please verify the values and retry.';
      setMessage({ kind: 'error', text: serverMsg });
    }
  };

  const handleReset = () => {
    setForm(initial);
    setAllowedText((initial.allowed_models ?? []).join(', '));
    setMessage(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/40 p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-extrabold text-black dark:text-white tracking-tight">
          {tierLabel}
        </h4>
        <label className="flex items-center gap-2 text-[11px] font-bold text-black/60 dark:text-white/60">
          <input
            type="checkbox"
            checked={form.enforced}
            onChange={(e) => setForm((prev) => ({ ...prev, enforced: e.target.checked }))}
            className="h-4 w-4"
          />
          Enforced
        </label>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <NumberField
          label="Daily input tokens"
          value={form.daily_input_tokens}
          onChange={handleNumber('daily_input_tokens')}
        />
        <NumberField
          label="Daily output tokens"
          value={form.daily_output_tokens}
          onChange={handleNumber('daily_output_tokens')}
        />
        <NumberField
          label="Monthly input tokens"
          value={form.monthly_input_tokens}
          onChange={handleNumber('monthly_input_tokens')}
        />
        <NumberField
          label="Monthly output tokens"
          value={form.monthly_output_tokens}
          onChange={handleNumber('monthly_output_tokens')}
        />
        <NumberField
          label="Max input tokens per call"
          value={form.max_input_tokens_per_call}
          onChange={handleNumber('max_input_tokens_per_call')}
        />
        <NumberField
          label="Soft-cap percent (0..100)"
          value={form.soft_cap_percent}
          onChange={handleNumber('soft_cap_percent')}
          min={0}
          max={100}
        />
        <NumberField
          label="Reservation TTL (seconds, 30..3600)"
          value={form.reservation_ttl_seconds}
          onChange={handleNumber('reservation_ttl_seconds')}
          min={30}
          max={3600}
        />
      </div>

      <label className="block mt-4 text-[11px] font-bold text-black/60 dark:text-white/60">
        Allowed models (comma-separated; empty = any model the provider supports)
      </label>
      <textarea
        value={allowedText}
        onChange={(e) => setAllowedText(e.target.value)}
        rows={2}
        className="mt-1 w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black/40 px-3 py-2 text-sm text-black dark:text-white"
        placeholder="e.g. claude-3-5-sonnet, claude-3-haiku"
      />

      {message && (
        <div
          className={`mt-4 rounded-lg border p-3 text-xs ${
            message.kind === 'success'
              ? 'bg-green-500/10 border-green-500/20 text-green-500'
              : 'bg-red-500/10 border-red-500/20 text-red-500'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="mt-5 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={handleReset}
          disabled={saving}
          className="rounded-xl border border-black/10 dark:border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-black dark:text-white disabled:opacity-40"
        >
          Discard changes
        </button>
        <button
          type="submit"
          disabled={saving}
          className="rounded-xl bg-brand px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white shadow-sm disabled:opacity-40 flex items-center gap-2"
        >
          <Save size={12} strokeWidth={3} />
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {initial.updated_at && (
        <p className="mt-3 text-[10px] text-black/40 dark:text-white/40">
          Last updated {new Date(initial.updated_at).toLocaleString()}
          {initial.updated_by ? ` by ${initial.updated_by}` : ''}
        </p>
      )}
    </form>
  );
}

// ---------------------------------------------------------------------------
// Small leaves
// ---------------------------------------------------------------------------

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  min?: number;
  max?: number;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] font-bold text-black/60 dark:text-white/60">
        {label}
      </span>
      <input
        type="number"
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        className="mt-1 w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black/40 px-3 py-2 text-sm text-black dark:text-white"
      />
    </label>
  );
}

function labelFor(tier: EditableTier): string {
  switch (tier) {
    case 'pro_managed':
      return 'Pro Managed (platform-key users)';
    case 'admin':
      return 'Admin (platform-key users)';
    default:
      return tier;
  }
}
