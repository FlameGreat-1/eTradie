import type { ReactNode } from 'react';
import { Lock, Sparkles } from 'lucide-react';
import { useTierGate, type TierGateKey } from '@/features/auth/hooks/useTierGate';

interface ProFeatureLockProps {
  /**
   * Which canonical gate copy to render. Maps 1:1 to the TIER_GATE_COPY
   * map in useTierGate so marketing wording stays in one place.
   */
  feature: TierGateKey;
  /**
   * The Pro-only UI to render when the user is entitled. Rendered as
   * children so each section keeps full control of its own layout.
   */
  children: ReactNode;
  /**
   * Optional override variant. 'overlay' (default) renders the full
   * children dimmed underneath the lock card; 'replace' hides the
   * children entirely and renders only the lock card. Use 'replace'
   * for surfaces where dimmed children would still leak sensitive
   * controls (e.g. an API-key input).
   */
  variant?: 'overlay' | 'replace';
  /**
   * Optional badge label shown on the locked card. Defaults to
   * 'Pro Feature' to match the product spec.
   */
  badge?: string;
}

/**
 * ProFeatureLock renders the canonical Pro-only locked state used
 * across every settings section. When the current user is on Free,
 * the children are visually disabled and a single upgrade CTA is
 * shown; when the user is Pro/Admin the children render unchanged
 * with zero runtime overhead beyond the tier check.
 *
 * The lock is a UX affordance only. The backend is the authoritative
 * gate (gateway 403, execution/management PermissionDenied, engine
 * tier-aware ProcessorConfig). Bypassing the UI does not grant access.
 */
export default function ProFeatureLock({
  feature,
  children,
  variant = 'overlay',
  badge = 'Pro Feature',
}: ProFeatureLockProps) {
  const { shouldLock, copy, openUpgradeModal } = useTierGate();

  if (!shouldLock) {
    return <>{children}</>;
  }

  const { title, body } = copy(feature);

  const lockCard = (
    <div
      role="region"
      aria-label={`${title} — ${badge}`}
      className="rounded-xl border border-brand/30 bg-brand/5 p-5 space-y-3"
    >
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1 rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-semibold text-brand uppercase tracking-wider">
          <Sparkles size={10} /> {badge}
        </span>
        <span className="text-xs font-semibold text-content">{title}</span>
      </div>
      <p className="text-xs text-content-muted leading-relaxed">{body}</p>
      <button
        type="button"
        onClick={openUpgradeModal}
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-[11px]
                   font-semibold text-black hover:bg-brand-dark transition-colors"
      >
        <Lock size={11} /> Upgrade to Pro
      </button>
    </div>
  );

  if (variant === 'replace') {
    return lockCard;
  }

  return (
    <div className="relative">
      <div
        className="pointer-events-none select-none opacity-40"
        aria-hidden="true"
        inert=""
      >
        {children}
      </div>
      <div className="mt-3">{lockCard}</div>
    </div>
  );
}
