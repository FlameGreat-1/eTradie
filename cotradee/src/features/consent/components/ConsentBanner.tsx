/**
 * Bottom-of-viewport cookie-consent banner.
 *
 * Rendering rules (EDPB 2022 'Cookie banner taskforce' guidance):
 *
 *   - Three equal-weight choices: Accept all / Reject all / Customise.
 *     The Reject button must NOT be visually de-emphasised relative
 *     to the Accept button. Both are .consent-btn-primary.
 *   - No close button. The banner cannot be dismissed by clicking
 *     away, pressing Escape, or scrolling. Implicit consent is not
 *     consent.
 *   - Suppressed on /cookie so the user reading the full policy is
 *     not occluded by the banner; the choice persists on close.
 *   - Hidden until ConsentProvider has finished hydrating so the
 *     banner does not flash for a returning visitor who already has
 *     a recorded decision.
 */

import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useConsent } from '../useConsent';
import '../consent.css';

export default function ConsentBanner() {
  const consent = useConsent();
  const location = useLocation();

  // Suppress on the policy page itself.
  const onPolicyPage = location.pathname === '/cookie';

  // The banner appears only when (a) we have finished hydrating, (b) a
  // decision is required, (c) the preferences modal is not already
  // open (so the user does not see both), and (d) we are not on the
  // policy page.
  const visible =
    consent.hydrated &&
    consent.needsDecision &&
    !consent.preferencesOpen &&
    !onPolicyPage;

  // Defensive scroll-lock parity with the rest of the app's modals.
  useEffect(() => {
    if (!visible) return;
    const prev = document.body.style.overflow;
    // Banner does NOT lock scroll — unlike a modal, it is non-modal.
    // We still set this to '' explicitly so a previously-locked state
    // from a different modal does not bleed through.
    document.body.style.overflow = prev;
  }, [visible]);

  if (!visible) return null;

  const handleAcceptAll = () => {
    void consent.acceptAll();
  };
  const handleRejectAll = () => {
    void consent.rejectAll();
  };
  const handleCustomise = () => {
    consent.openPreferences();
  };

  return (
    <div
      className="consent-banner-wrap"
      role="region"
      aria-label="Cookie consent"
    >
      <div className="consent-banner">
        <div className="consent-banner-row">
          <div className="consent-banner-text">
            <strong>Cookies on Exoper.</strong>{' '}
            We use cookies that are strictly necessary to operate the platform.
            With your permission we also use a small number of functional and
            analytics cookies to improve the experience. Read our{' '}
            <Link to="/cookie">Cookie Policy</Link> for full detail. You can change
            this choice at any time from Cookie Preferences in the footer.
          </div>
          <div className="consent-banner-actions">
            <button
              type="button"
              className="consent-btn"
              onClick={handleCustomise}
            >
              Customise
            </button>
            <button
              type="button"
              className="consent-btn"
              onClick={handleRejectAll}
            >
              Reject all
            </button>
            <button
              type="button"
              className="consent-btn consent-btn-primary"
              onClick={handleAcceptAll}
            >
              Accept all
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
