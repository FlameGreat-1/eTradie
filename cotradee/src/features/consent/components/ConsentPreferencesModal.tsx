/**
 * Cookie preferences modal.
 *
 * Differences from the banner:
 *
 *   - Dismissable via Escape, backdrop click, or the X button. The
 *     user is reviewing an existing decision (or refining one before
 *     accepting); dismissing leaves the prior decision intact.
 *   - Body scroll locked while visible, matching the rest of the
 *     app's modals (UpgradeModal sets the same lock).
 *   - Strictly Necessary is rendered as a disabled, always-on row.
 *     The label MUST match the Cookie Policy verbatim (PLAN.md §7).
 *   - Local toggle state is seeded from the current decision so a
 *     user opening the modal sees their saved choices, not a reset.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { useConsent } from '../useConsent';
import type { ConsentDecision } from '../types';
import '../consent.css';

export default function ConsentPreferencesModal() {
  const consent = useConsent();
  const [draft, setDraft] = useState<ConsentDecision>(consent.decision);
  const [saving, setSaving] = useState(false);

  // Seed local toggle state from the live decision every time the
  // modal is opened so a 'Reject all' issued by the banner is
  // reflected when the user later opens preferences.
  useEffect(() => {
    if (consent.preferencesOpen) {
      setDraft(consent.decision);
    }
  }, [consent.preferencesOpen, consent.decision]);

  // Standard modal lifecycle: lock body scroll while open, bind
  // Escape to close. Both are released on close / unmount.
  useEffect(() => {
    if (!consent.preferencesOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') consent.closePreferences();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [consent.preferencesOpen, consent]);

  if (!consent.preferencesOpen) return null;

  const toggle = (key: keyof ConsentDecision) =>
    setDraft((d) => ({ ...d, [key]: !d[key] }));

  const doSave = async () => {
    setSaving(true);
    try {
      await consent.saveCustom(draft);
      consent.closePreferences();
    } catch {
      // Toast already surfaced by the context; keep modal open so the
      // user can retry without losing their toggle state.
    } finally {
      setSaving(false);
    }
  };

  const doAcceptAll = async () => {
    setSaving(true);
    try {
      await consent.acceptAll();
      consent.closePreferences();
    } finally {
      setSaving(false);
    }
  };

  const doRejectAll = async () => {
    setSaving(true);
    try {
      await consent.rejectAll();
      consent.closePreferences();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="consent-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Cookie preferences"
      onClick={consent.closePreferences}
    >
      <div
        className="consent-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="consent-modal-header">
          <div>
            <div className="consent-modal-title">Cookie preferences</div>
            <div className="consent-modal-subtitle">
              Choose which optional cookies Exoper may use. Strictly
              necessary cookies are required for the platform to
              function and cannot be disabled. See our{' '}
              <Link to="/cookie" onClick={consent.closePreferences}>Cookie Policy</Link> for
              full detail.
            </div>
          </div>
          <button
            type="button"
            className="consent-modal-close"
            onClick={consent.closePreferences}
            aria-label="Close cookie preferences"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body — one category per row */}
        <div className="consent-modal-body">
          {/* Strictly Necessary — always on. */}
          <div className="consent-category">
            <div className="consent-category-header">
              <div className="consent-category-title">Strictly necessary</div>
              <span className="consent-always-on">Always on</span>
            </div>
            <div className="consent-category-desc">
              Required for the platform to function. Authentication, session
              management, and CSRF protection cookies. These cannot be
              disabled.
            </div>
          </div>

          {/* Functional — genuinely gates theme persistence in
              ThemeProvider. Granting writes the chosen theme to
              localStorage so the next visit is remembered; revoking
              deletes the stored key and keeps the theme only for the
              current tab. See providers/ThemeProvider.tsx. */}
          <div className="consent-category">
            <div className="consent-category-header">
              <div className="consent-category-title">Functional</div>
              <button
                type="button"
                className="consent-toggle"
                data-checked={draft.functional}
                aria-pressed={draft.functional}
                aria-label="Toggle functional cookies"
                onClick={() => toggle('functional')}
                disabled={saving}
              />
            </div>
            <div className="consent-category-desc">
              Remember your theme preference across visits. When
              disabled, your theme choice still applies for the current
              tab but is not stored on your device.
            </div>
          </div>

          {/* Analytics — dormant. No analytics SDK is installed and
              no component consumes useHasConsent('analytics'). The
              toggle is preserved so a future rollout honours the
              user's pre-recorded preference rather than treating the
              decision as fresh; the description is explicit that
              nothing is collected today. */}
          <div className="consent-category">
            <div className="consent-category-header">
              <div className="consent-category-title">Analytics</div>
              <button
                type="button"
                className="consent-toggle"
                data-checked={draft.analytics}
                aria-pressed={draft.analytics}
                aria-label="Toggle analytics cookies"
                onClick={() => toggle('analytics')}
                disabled={saving}
              />
            </div>
            <div className="consent-category-desc">
              Not currently in use. If introduced in the future, these
              cookies would help us collect aggregated, pseudonymous
              usage data to improve reliability and performance. Your
              choice here is recorded today and will be honoured
              automatically if analytics is ever enabled. Never used
              for advertising and never combined with broker or
              trading data.
            </div>
          </div>
        </div>

        {/* Action row */}
        <div className="consent-modal-actions">
          <button
            type="button"
            className="consent-btn"
            onClick={doRejectAll}
            disabled={saving}
          >
            Reject all
          </button>
          <button
            type="button"
            className="consent-btn"
            onClick={doAcceptAll}
            disabled={saving}
          >
            Accept all
          </button>
          <button
            type="button"
            className="consent-btn consent-btn-primary"
            onClick={doSave}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save preferences'}
          </button>
        </div>
      </div>
    </div>
  );
}
