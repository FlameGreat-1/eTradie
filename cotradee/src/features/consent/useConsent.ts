/**
 * Public hook surface for the cookie-consent feature.
 *
 * useConsent       — full ConsentState (used by the banner, modal,
 *                    settings page, and AuthContext attach-on-login).
 * useHasConsent    — boolean for a single category. Read by gates
 *                    and conditional analytics initialisation.
 * useIsConsentOpen — boolean indicating the preferences modal is
 *                    currently open; used by the footer link to no-op
 *                    if the modal is already on screen.
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

export function useHasConsent(category: Category): boolean {
  const ctx = useContext(ConsentContext);
  if (!ctx) return false;
  return ctx.decision[category];
}

export function useIsConsentOpen(): boolean {
  const ctx = useContext(ConsentContext);
  if (!ctx) return false;
  return ctx.preferencesOpen;
}
