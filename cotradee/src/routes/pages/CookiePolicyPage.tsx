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
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
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
        Exoper uses cookies in the following categories. We do not use advertising cookies
        and we do not sell cookie data to third parties.
      </p>
      <ul>
        <li><strong>Strictly necessary</strong> — required for the Platform to function</li>
        <li><strong>Functional</strong> — remember your preferences and settings</li>
        <li><strong>Analytics</strong> — help us understand how the Platform is used</li>
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
          <strong>Authentication tokens</strong> — keep you signed in across pages and
          sessions, and protect your account from unauthorised access.
        </li>
        <li>
          <strong>Session identifiers</strong> — maintain the state of your current session
          (for example, which workspace or symbol you have selected).
        </li>
        <li>
          <strong>CSRF tokens</strong> — protect form submissions and API requests against
          cross-site request forgery.
        </li>
        <li>
          <strong>Security cookies</strong> — detect and mitigate abusive traffic,
          credential-stuffing attempts, and other security events.
        </li>
      </ul>

      {/* 5. Functional */}
      <h2 id="functional">5. Functional Cookies</h2>
      <p>
        Functional cookies remember choices you have made so the Platform behaves the way
        you expect on each visit.
      </p>
      <ul>
        <li>
          <strong>Theme preference</strong> — remembers whether you have selected the
          light or dark interface.
        </li>
        <li>
          <strong>Workspace layout</strong> — remembers your selected timeframe, active
          symbol, and dashboard configuration.
        </li>
        <li>
          <strong>Locale &amp; region</strong> — remembers your preferred language and
          regional formatting.
        </li>
        <li>
          <strong>UI dismissals</strong> — remembers banners, tips, and onboarding steps
          you have already dismissed.
        </li>
      </ul>

      {/* 6. Analytics */}
      <h2 id="analytics">6. Analytics Cookies</h2>
      <p>
        Analytics cookies help us understand how the Platform is used so we can improve
        reliability, performance, and feature quality. They collect aggregated, pseudonymous
        usage data such as page views, navigation paths, feature engagement, error rates,
        and load performance.
      </p>
      <p>
        Analytics data is not used for advertising and is not combined with broker or
        trading account data. Where reasonably possible, IP addresses are truncated or
        anonymised before analysis.
      </p>

      {/* 7. Third-Party */}
      <h2 id="third-party">7. Third-Party Cookies</h2>
      <p>
        Certain features rely on trusted third-party services that may set their own
        cookies when you interact with them:
      </p>
      <ul>
        <li>
          <strong>Paddle and Lemon Squeezy</strong> — set cookies during checkout and
          billing management. These cookies are governed by the respective provider&rsquo;s
          cookie and privacy policies.
        </li>
        <li>
          <strong>Google (OAuth sign-in)</strong> — if you sign in with Google, Google may
          set cookies as part of its authentication flow.
        </li>
        <li>
          <strong>Cloud infrastructure providers</strong> — may set cookies for traffic
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
          <strong>Session cookies</strong> — deleted automatically when you close your
          browser. Used for short-lived session state.
        </li>
        <li>
          <strong>Persistent cookies</strong> — remain on your device for a defined period
          (typically between 7 days and 12 months, depending on the cookie&rsquo;s purpose)
          or until you delete them.
        </li>
      </ul>

      {/* 9. Control */}
      <h2 id="control">9. Your Control Over Cookies</h2>
      <p>You can control cookies in several ways:</p>
      <ul>
        <li>
          <strong>Browser settings</strong> — all modern browsers allow you to view, block,
          or delete cookies. Consult your browser&rsquo;s help documentation for instructions.
        </li>
        <li>
          <strong>Cookie preferences in the Platform</strong> — where applicable, you can
          adjust non-essential cookie categories from your account settings.
        </li>
        <li>
          <strong>Opt-out tools</strong> — third-party providers may offer their own
          opt-out mechanisms; see the links in Section&nbsp;7.
        </li>
      </ul>
      <div className="legal-callout">
        <p>
          <strong>Blocking strictly necessary cookies will prevent the Platform from
          functioning.</strong> You will not be able to sign in, maintain a session, or use
          core features. Blocking functional or analytics cookies will not prevent core
          functionality but may degrade your experience.
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
        shown at the top of this page. Material changes will be communicated through the
        Platform or by email.
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
