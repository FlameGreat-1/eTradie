/**
 * Canonical types for the cookie-consent feature.
 *
 * Every shape here is shared between the storage layer, the API
 * layer, the React context, and the UI components, so a typo in one
 * place produces a TypeScript compile error elsewhere rather than a
 * silent runtime mismatch.
 *
 * The category names ('functional' | 'analytics') MUST match the
 * server-side constants in src/consent/models.go and the labels in
 * cotradee/src/routes/pages/CookiePolicyPage.tsx verbatim. PLAN.md
 * section 7 forbids drift between the policy text and the actual
 * implementation.
 */

/**
 * The optional cookie categories the user can toggle.
 *
 * Strictly-necessary cookies (auth_token / refresh_token / csrf_token)
 * are deliberately absent from this union: they are always on, cannot
 * be opted out of under ePrivacy Directive Art. 5(3), and are not
 * stored in the consent record.
 */
export type Category = 'functional' | 'analytics';

/**
 * The per-category boolean map persisted on every consent decision.
 * Always carries both keys explicitly so an absent key is never
 * ambiguous between 'opted out' and 'never asked'.
 */
export interface ConsentDecision {
  functional: boolean;
  analytics: boolean;
}

export function rejectAllDecision(): ConsentDecision {
  return { functional: false, analytics: false };
}

export function acceptAllDecision(): ConsentDecision {
  return { functional: true, analytics: true };
}

/**
 * Server-side record returned by the consent API. user_id is null
 * for purely-anonymous decisions; anonymous_id is always populated.
 */
export interface ConsentRecord {
  id: string;
  user_id: string | null;
  anonymous_id: string;
  policy_version: string;
  categories: ConsentDecision;
  created_at: string;
}

/**
 * Public state surface exposed by useConsent(). Pure data + actions
 * — no DOM, no React internals. UI components consume this and the
 * context provider produces it.
 */
export interface ConsentState {
  /** True once the initial hydrate (local + server reconcile) has finished. */
  hydrated: boolean;
  /** True when no acceptable decision exists yet — banner should be visible. */
  needsDecision: boolean;
  /** True when the user has explicitly invoked the Preferences modal. */
  preferencesOpen: boolean;
  /** Current per-category opt-in map. Defaults to all-false until a decision is made. */
  decision: ConsentDecision;
  /** The browser-stable anonymous id minted on first visit. */
  anonymousId: string;
  /** Policy version of the latest recorded decision; '' when none. */
  recordedPolicyVersion: string;
  /**
   * True when the user actively made a consent decision in the
   * current browser tab session (not loaded from pre-existing local
   * storage). Used by ConsentAuthBridge to decide whether the
   * current anonymous_id is safe to attach to a freshly-logged-in
   * user: attaching a stranger's decision (e.g. a shared computer)
   * would corrupt the legal audit trail.
   */
  decisionMadeThisSession: boolean;

  /** Accept every optional category and persist. */
  acceptAll: () => Promise<void>;
  /** Reject every optional category and persist. */
  rejectAll: () => Promise<void>;
  /** Persist an arbitrary per-category choice (from the preferences modal). */
  saveCustom: (decision: ConsentDecision) => Promise<void>;
  /** Open the preferences modal (no persistence; UI-only). */
  openPreferences: () => void;
  /** Close the preferences modal (no persistence; UI-only). */
  closePreferences: () => void;
  /** Hook used by AuthContext to attach the anonymous id to the new user_id post-login. */
  attachToCurrentUser: () => Promise<void>;
}

/**
 * The current cookie-policy revision. Bumping this string forces every
 * user to be re-prompted, regardless of any previously-recorded
 * decision: the context compares this constant to recordedPolicyVersion
 * and sets needsDecision=true whenever they differ.
 *
 * Matches the 'Effective:' date displayed on the Cookie Policy page.
 * Change in lockstep with the legal document; a mismatch is a
 * compliance defect.
 *
 * Bumped to 2026-05-12 when:
 *   - Functional consent was wired through to ThemeProvider so the
 *     toggle now genuinely gates theme persistence.
 *   - The Analytics description was corrected to reflect that the
 *     SPA performs no analytics processing today; the toggle is
 *     preserved for forward compatibility and to honour the user's
 *     future-state preference, but the prior copy that implied
 *     active collection has been replaced.
 */
export const CONSENT_POLICY_VERSION = '2026-05-12';
