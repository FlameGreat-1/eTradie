import { useAuth } from '@/features/auth';

/**
 * Canonical free-tier copy. Mirrors the product spec verbatim so
 * marketing wording changes in one place instead of scattered
 * across each settings section.
 */
export const TIER_GATE_COPY = {
  symbols: {
    title: '1 active symbol',
    body: 'Free tier is restricted to 1 active symbol. Upgrade to Pro for unlimited tracking.',
  },
  scheduling: {
    title: 'Automated scheduling',
    body: 'Automated cycles are restricted to Pro users. You can still trigger 1 manual analysis per 24 hours from the dashboard.',
  },
  execution: {
    title: 'Automated trade execution',
    body: 'Automated Trade Execution is restricted to Pro users. You will only receive analysis alerts.',
  },
  management: {
    title: 'Trade management',
    body: 'Trade Management (Watchers, Trailing Stops, Breakeven) is a Pro feature.',
  },
  platformKey: {
    title: 'Platform AI Key',
    body: 'Platform AI Key is only available on the Pro Managed tier. Please provide your own API key or upgrade your plan.',
  },
} as const;

export type TierGateKey = keyof typeof TIER_GATE_COPY;

export interface TierGate {
  /** Resolved tier (defaults to 'free' when the profile has not loaded yet). */
  tier: 'free' | 'pro_byok' | 'pro_managed';
  /** True iff the user is on the free tier AND is not an admin. */
  isFree: boolean;
  /** True for the admin role. Admins are never gated by tier. */
  isAdmin: boolean;
  /** Convenience: pro_byok specifically. */
  isProBYOK: boolean;
  /** Convenience: pro_managed specifically. */
  isProManaged: boolean;
  /** True iff the SPA should lock a Pro-only surface for this user. */
  shouldLock: boolean;
  /** Copy lookup for the named gate. */
  copy: (key: TierGateKey) => { title: string; body: string };
  /** Opens the upgrade modal via the shared window event. */
  openUpgradeModal: () => void;
}

/**
 * useTierGate is the SPA's single source of truth for free-tier UI gating.
 *
 * Every Pro-only section (Symbols cap, Execution form, LLM platform-key
 * toggle, Management watcher list, etc.) reads from this hook so the
 * lock decision, telemetry, and copy stay consistent. The hook does NOT
 * fetch anything; it derives state from the already-loaded AuthContext.
 *
 * Server-side enforcement lives in the gateway, billing, engine,
 * execution, and management services and is the authoritative gate.
 * This hook is for UX only — a forged client-side bypass cannot grant
 * access to a Pro-only path because the backend rejects it.
 */
export function useTierGate(): TierGate {
  const { user } = useAuth();
  const tier = (user?.tier ?? 'free') as TierGate['tier'];
  const isAdmin = user?.role === 'admin';
  const isFree = tier === 'free' && !isAdmin;
  const isProBYOK = tier === 'pro_byok';
  const isProManaged = tier === 'pro_managed';

  return {
    tier,
    isFree,
    isAdmin,
    isProBYOK,
    isProManaged,
    shouldLock: isFree,
    copy: (key) => TIER_GATE_COPY[key],
    openUpgradeModal: () => window.dispatchEvent(new Event('open-upgrade-modal')),
  };
}
