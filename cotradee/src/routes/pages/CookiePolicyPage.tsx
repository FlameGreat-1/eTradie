import { Link } from 'react-router-dom';
import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'what-are-cookies', title: '2. What Cookies Are' },
  { id: 'categories', title: '3. Categories We Use' },
  { id: 'strictly-necessary', title: '4. Strictly Necessary' },
  { id: 'functional', title: '5. Functional' },
  { id: 'analytics', title: '6. Analytics' },
  { id: 'third-party', title: '7. Third-Party Cookies' },
  { id: 'retention', title: '8. Retention' },
  { id: 'control', title: '9. Your Control' },
  { id: 'do-not-track', title: '10. Do Not Track' },
  { id: 'changes', title: '11. Changes' },
  { id: 'contact', title: '12. Contact' },
];

export default function CookiePolicyPage() {
  return (
    <LegalPageLayout
      title="Cookie Policy"
      subtitle="This policy explains what cookies and similar technologies Exoper uses, why we use them, and how you can control them."
      effectiveDate="12 May 2026"
      lastUpdated="12 May 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        This Cookie Policy describes how Exoper (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or
        &ldquo;our&rdquo;) uses cookies and similar tracking technologies on the Exoper
        platform (&ldquo;Platform&rdquo;). It should be read together with our{' '}
        <Link to="/privacy">Privacy Policy</Link>, which explains how we handle personal data
        more broadly.
      </p>
      <p>
        By continuing to use the Platform, you consent to the use of cookies as described
        in this policy. You can withdraw or change your consent at any time using the
        controls described in Section&nbsp;9.
      </p>

      {/* 2. What Cookies Are */}
      <h2 id="what-are-cookies">2. What Cookies Are</h2>
      <p>
        Cookies are small text files stored on your device when you visit a website. They
        allow the site to recognise your device on subsequent visits, remember your
        preferences, and provide a functional, secure experience.
      </p>
      <p>
        Where this policy refers to &ldquo;cookies,&rdquo; we mean cookies and equivalent
        technologies such as local storage, session storage, and similar device-side
        storage mechanisms used by modern web applications.
      </p>

      {/* 3. Categories */}
      <h2 id="categories">3. Categories We Use</h2>
      <p>
        Exoper uses cookies in the following categories. We do not use advertising cookies,
        we do not sell cookie data to third parties, and we do not currently operate any
        analytics or tracking pixels of our own.
      </p>
      <ul>
        <li><strong>Strictly necessary</strong> &mdash; required for the Platform to function</li>
        <li><strong>Functional</strong> &mdash; remember your preferences and settings</li>
        <li><strong>Analytics</strong> &mdash; currently not in use; see Section&nbsp;6</li>
      </ul>

      {/* 4. Strictly Necessary */}
      <h2 id="strictly-necessary">4. Strictly Necessary Cookies</h2>
      <p>
        These cookies are essential. The Platform cannot function correctly without them
        and they cannot be disabled. They do not store personally identifiable information
        beyond what is required to operate the service.
      </p>
      <ul>
        <li>
          <strong>Authentication tokens</strong> &mdash; keep you signed in across pages and
          sessions, and protect your account from unauthorised access.
        </li>
        <li>
          <strong>Session identifiers</strong> &mdash; maintain the state of your current session
          (for example, which workspace or symbol you have selected).
        </li>
        <li>
          <strong>CSRF tokens</strong> &mdash; protect form submissions and API requests against
          cross-site request forgery.
        </li>
        <li>
          <strong>Security cookies</strong> &mdash; detect and mitigate abusive traffic,
          credential-stuffing attempts, and other security events.
        </li>
      </ul>

      {/* 5. Functional */}
      <h2 id="functional">5. Functional Cookies</h2>
      <p>
        Functional cookies remember choices you have made so the Platform behaves the way
        you expect on each visit. They are written only after you grant Functional consent
        in the cookie preferences and are removed from your device if you later withdraw
        consent.
      </p>
      <ul>
        <li>
          <strong>Theme preference</strong> &mdash; remembers whether you have selected the
          light or dark interface across visits. When Functional consent is not granted,
          your theme choice still applies for the current tab but is not stored on your
          device.
        </li>
      </ul>
      <p>
        Other preference-style features (workspace layout, dismissed banners, locale
        formatting) may be added in future. When they are, they will be added to this
        section and the policy version will be bumped so every user is re-prompted before
        any new device-side storage begins.
      </p>

      {/* 6. Analytics — dormant. */}
      <h2 id="analytics">6. Analytics Cookies</h2>
      <div className="legal-callout">
        <p>
          <strong>Currently not in use.</strong> Exoper does not operate any analytics
          or tracking pixels of its own at this time. No analytics cookies are set on
          your device when you visit the Platform.
        </p>
      </div>
      <p>
        The Analytics toggle in your cookie preferences is preserved so that, if
        analytics is ever introduced, your prior choice is honoured automatically and you
        are not asked to decide again about a category you have already considered.
      </p>
      <p>
        If introduced in the future, analytics cookies would help us collect aggregated,
        pseudonymous usage data such as page views, navigation paths, feature engagement,
        error rates, and load performance. Analytics data would never be used for
        advertising and would never be combined with broker or trading account data.
        Where reasonably possible, IP addresses would be truncated or anonymised before
        analysis.
      </p>
      <p>
        Before any analytics processing begins, we will update this policy with the name
        of the analytics provider, the data categories collected, the retention period,
        and the lawful basis; we will bump the policy version so every user is
        re-prompted; and any prior &lsquo;reject&rsquo; choice recorded under this dormant
        category will be honoured automatically.
      </p>

      {/* 7. Third-Party */}
      <h2 id="third-party">7. Third-Party Cookies</h2>
      <p>
        Certain features rely on trusted third-party services that may set their own
        cookies when you interact with them:
      </p>
      <ul>
        <li>
          <strong>Paddle and Lemon Squeezy</strong> &mdash; set cookies during checkout and
          billing management. These cookies are governed by the respective provider&rsquo;s
          cookie and privacy policies.
        </li>
        <li>
          <strong>Google (OAuth sign-in)</strong> &mdash; if you sign in with Google, Google may
          set cookies as part of its authentication flow.
        </li>
        <li>
          <strong>Cloud infrastructure providers</strong> &mdash; may set cookies for traffic
          routing, load balancing, and security purposes.
        </li>
      </ul>
      <p>
        Exoper does not control these third-party cookies. Please refer to the respective
        provider&rsquo;s policies for details:
      </p>
      <ul>
        <li>Paddle: <a href="https://www.paddle.com/legal/privacy" target="_blank" rel="noopener noreferrer">paddle.com/legal/privacy</a></li>
        <li>Lemon Squeezy: <a href="https://www.lemonsqueezy.com/privacy" target="_blank" rel="noopener noreferrer">lemonsqueezy.com/privacy</a></li>
        <li>Google: <a href="https://policies.google.com/technologies/cookies" target="_blank" rel="noopener noreferrer">policies.google.com/technologies/cookies</a></li>
      </ul>

      {/* 8. Retention */}
      <h2 id="retention">8. Cookie Retention</h2>
      <p>
        Cookies fall into two retention categories:
      </p>
      <ul>
        <li>
          <strong>Session cookies</strong> &mdash; deleted automatically when you close your
          browser. Used for short-lived session state.
        </li>
        <li>
          <strong>Persistent cookies</strong> &mdash; remain on your device for a defined period
          (typically between 7 days and 12 months, depending on the cookie&rsquo;s purpose)
          or until you delete them.
        </li>
      </ul>

      {/* 9. Control */}
      <h2 id="control">9. Your Control Over Cookies</h2>
      <p>You can control cookies in several ways:</p>
      <ul>
        <li>
          <strong>Browser settings</strong> &mdash; all modern browsers allow you to view, block,
          or delete cookies. Consult your browser&rsquo;s help documentation for instructions.
        </li>
        <li>
          <strong>Cookie preferences in the Platform</strong> &mdash; you can adjust the
          Functional and Analytics categories at any time from the Cookie Preferences
          control. Withdrawing Functional consent deletes the stored preference and stops
          further writes immediately.
        </li>
        <li>
          <strong>Opt-out tools</strong> &mdash; third-party providers may offer their own
          opt-out mechanisms; see the links in Section&nbsp;7.
        </li>
      </ul>
      <div className="legal-callout">
        <p>
          <strong>Blocking strictly necessary cookies will prevent the Platform from
          functioning.</strong> You will not be able to sign in, maintain a session, or use
          core features. Blocking Functional cookies will not prevent core functionality
          but means your theme preference will not be remembered between visits.
        </p>
      </div>

      {/* 10. Do Not Track */}
      <h2 id="do-not-track">10. Do Not Track</h2>
      <p>
        Some browsers transmit a &ldquo;Do Not Track&rdquo; (DNT) signal. There is no
        common industry standard for how DNT signals should be interpreted. At present, the
        Platform does not respond to DNT signals, but we honour any cookie preferences you
        have set through the controls described in Section&nbsp;9.
      </p>

      {/* 11. Changes */}
      <h2 id="changes">11. Changes to This Policy</h2>
      <p>
        We may update this Cookie Policy from time to time to reflect changes in technology,
        regulation, or our practices. The updated policy will be effective from the date
        shown at the top of this page. Material changes (including the introduction of any
        new cookie category) will be communicated through the Platform and will require a
        fresh consent decision before any new processing begins.
      </p>

      {/* 12. Contact */}
      <h2 id="contact">12. Contact</h2>
      <p>For questions about this Cookie Policy:</p>
      <ul>
        <li>Email: <a href="mailto:privacy@exoper.com">privacy@exoper.com</a></li>
        <li>Support: <Link to="/dashboard/support">Platform Support Centre</Link></li>
      </ul>
    </LegalPageLayout>
  );
}
