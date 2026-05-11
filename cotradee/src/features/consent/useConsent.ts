/**
 * Public hook surface for the cookie-consent feature.
 *
 * useConsent          — full ConsentState. Throws when not inside a
 *                       ConsentProvider; use this in surfaces that
 *                       are ALWAYS mounted under AppProvider.
 * useConsentOptional  — returns null when no provider is above. Use
 *                       in surfaces that might be rendered outside
 *                       AppProvider (error pages, storybook,
 *                       maintenance pages) so the consumer can
 *                       gracefully degrade rather than crashing.
 * useHasConsent       — boolean for a single category. Returns false
 *                       when no provider is mounted, so callers like
 *                       conditional analytics SDK initialisation
 *                       never throw.
 */

import { useContext } from 'react';
import { ConsentContext } from './ConsentContext';
import type { Category, ConsentState } from './types';

export function useConsent(): ConsentState {
  const ctx = useContext(ConsentContext);
  if (!ctx) {
    throw new Error('useConsent must be used within a ConsentProvider');
  }
  return ctx;
}

export function useConsentOptional(): ConsentState | null {
  const ctx = useContext(ConsentContext);
  return ctx ?? null;
}

export function useHasConsent(category: Category): boolean {
  const ctx = useContext(ConsentContext);
  if (!ctx) return false;
  return ctx.decision[category];
}
