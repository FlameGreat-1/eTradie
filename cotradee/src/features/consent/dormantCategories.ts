/**
 * Single source of truth for cookie-consent categories that are
 * intentionally dormant: present in the type system, the modal
 * toggle, the Cookie Policy text, and the server-side audit record,
 * but with NO runtime consumer in the SPA.
 *
 * The list is consumed by:
 *
 *   1. The CI guard in cotradee/scripts/check-consent-consumers.mjs,
 *      which fails the build when an active (non-dormant) category
 *      has zero consumers OR when a dormant category gains a
 *      consumer without being promoted here. Both directions of
 *      drift produce a loud CI failure.
 *
 *   2. (Future) UI surfaces that may want to visually mark a
 *      dormant row in the preferences modal. None do today; the
 *      Cookie Policy text carries the disclosure instead.
 *
 * Promoting a category from dormant to active is intentionally
 * cheap: delete its entry from this list, ship the SDK consumer in
 * the same MR, and bump CONSENT_POLICY_VERSION so every existing
 * user is re-prompted with the updated description. The CI guard
 * will refuse to merge a promotion that lacks a consumer, so the
 * hollow-toggle bug class cannot return without being noticed.
 */

import type { Category } from './types';

export const DORMANT_CATEGORIES: readonly Category[] = [
  // No analytics SDK is installed; the toggle is preserved for
  // forward compatibility (a future rollout must honour the user's
  // pre-recorded preference rather than treat the decision as
  // fresh). See cotradee/src/routes/pages/CookiePolicyPage.tsx §6
  // for the user-facing disclosure.
  'analytics',
] as const;
