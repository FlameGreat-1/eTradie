/**
 * Bottom-of-viewport cookie-consent banner.
 *
 * Rendering rules (EDPB 2022 'Cookie banner taskforce' guidance):
 *
 *   - Three equal-weight choices: Accept all / Reject all / Customise.
 *     Accept and Reject are BOTH rendered with a filled-button style
 *     so the visitor's eye is not drawn to one over the other. Only
 *     Customise (a navigation, not a decision) uses the outline style.
 *     The previous layout placed only Accept in the primary fill,
 *     which is the exact dark-pattern penalised in CNIL / EDPB / DPC
 *     enforcement actions.
 *   - No close button. The banner cannot be dismissed by clicking
 *     away, pressing Escape, or scrolling. Implicit consent is not
 *     consent.
 *   - Suppressed on /cookie so the user reading the full policy is
 *     not occluded by the banner; the choice persists on close.
 *   - Hidden until ConsentProvider has finished hydrating so the
 *     banner does not flash for a returning visitor who already has
 *     a recorded decision.
 */

import { memo, useCallback, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useConsent } from '../useConsent';
import '../consent.css';

function ConsentBanner() {
  const consent = useConsent();
  const location = useLocation();

  // Memoised so a re-render with the same path does not re-evaluate
  // (cheap, but it also makes the visibility decision a pure derived
  // value documented in one place).
  const onPolicyPage = useMemo(
    () => location.pathname === '/cookie',
    [location.pathname],
  );

  // The banner appears only when (a) we have finished hydrating, (b) a
  // decision is required, (c) the preferences modal is not already
  // open (so the user does not see both), and (d) we are not on the
  // policy page.
  const visible =
    consent.hydrated &&
    consent.needsDecision &&
    !consent.preferencesOpen &&
    !onPolicyPage;

  const handleAcceptAll = useCallback(() => {
    void consent.acceptAll();
  }, [consent]);
  const handleRejectAll = useCallback(() => {
    void consent.rejectAll();
  }, [consent]);
  const handleCustomise = useCallback(() => {
    consent.openPreferences();
  }, [consent]);

  if (!visible) return null;

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
              className="consent-btn consent-btn-reject"
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

export default memo(ConsentBanner);
