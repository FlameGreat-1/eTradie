/**
 * <ConsentGate category="analytics">{children}</ConsentGate>
 *
 * Declarative wrapper that renders its children only when the visitor
 * has actively granted consent for the named category. The default
 * fallback is null — the gate is invisible until consent is granted.
 *
 * Typical usage (when an analytics SDK is added):
 *
 *   <ConsentGate category="analytics">
 *     <AnalyticsBootstrap />
 *   </ConsentGate>
 *
 * The gate is reactive: revoking consent in the preferences modal
 * triggers an immediate unmount of the gated subtree, so any SDK
 * that registers global listeners on mount must also clean them up
 * on unmount. (This is standard React behaviour; flagged here so
 * future integrators do not assume the gate is fire-and-forget.)
 */

import type { ReactNode } from 'react';
import { useHasConsent } from './useConsent';
import type { Category } from './types';

interface ConsentGateProps {
  /** Optional cookie category required for the children to render. */
  category: Category;
  /** Rendered when consent is granted. */
  children: ReactNode;
  /** Rendered when consent is missing or denied. Defaults to null. */
  fallback?: ReactNode;
}

export default function ConsentGate({
  category,
  children,
  fallback = null,
}: ConsentGateProps) {
  const granted = useHasConsent(category);
  return <>{granted ? children : fallback}</>;
}
