import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'data-collected', title: '2. Data We Collect' },
  { id: 'broker-data', title: '3. Broker Connectivity' },
  { id: 'ai-data', title: '4. AI & Analysis Data' },
  { id: 'usage-analytics', title: '5. Usage Analytics' },
  { id: 'cookies', title: '6. Cookies' },
  { id: 'security', title: '7. Data Security' },
  { id: 'third-parties', title: '8. Third-Party Services' },
  { id: 'retention', title: '9. Data Retention' },
  { id: 'user-rights', title: '10. Your Rights' },
  { id: 'children', title: '11. Children' },
  { id: 'changes', title: '12. Changes' },
  { id: 'contact', title: '13. Contact' },
];

export default function PrivacyPage() {
  return (
    <LegalPageLayout
      title="Privacy Policy"
      subtitle="This policy explains what data Exoper collects, how it is used, and how it is protected. We are committed to transparency about our data practices."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        Exoper (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;) operates a
        structured trading infrastructure platform. This Privacy Policy explains how we
        collect, use, store, and protect personal data when you use the Exoper platform
        (&ldquo;Platform&rdquo;).
      </p>
      <p>
        By using the Platform, you consent to the data practices described in this policy.
        If you do not agree, please do not use the Platform.
      </p>

      {/* 2. Data We Collect */}
      <h2 id="data-collected">2. Data We Collect</h2>
      <h3>2.1 Account Information</h3>
      <p>When you register, we collect:</p>
      <ul>
        <li>Name and username</li>
        <li>Email address</li>
        <li>Password (stored as a bcrypt hash — we never store plaintext passwords)</li>
        <li>Account preferences and settings</li>
        <li>Subscription tier and billing status</li>
      </ul>

      <h3>2.2 Profile &amp; Settings Data</h3>
      <p>As you configure the Platform, we store:</p>
      <ul>
        <li>Active trading symbols and instrument preferences</li>
        <li>Execution configuration (mode, risk parameters, position sizing rules)</li>
        <li>Cycle interval and scheduling preferences</li>
        <li>LLM provider preferences (provider name and model — not your API key in plaintext)</li>
      </ul>

      {/* 3. Broker Connectivity */}
      <h2 id="broker-data">3. Broker Connectivity Data</h2>
      <div className="legal-callout">
        <p>
          <strong>Broker credentials are stored encrypted at rest using AES-256 encryption.
          We do not transmit your broker credentials to third parties beyond what is
          necessary to establish your MT5 connection.</strong>
        </p>
      </div>
      <p>When you connect a broker account, we may process and store:</p>
      <ul>
        <li>Broker connection type (MetaAPI or ZeroMQ EA)</li>
        <li>MT5 account identifiers (server, login reference)</li>
        <li>EA authentication tokens (encrypted at rest)</li>
        <li>Connection status and health metrics</li>
      </ul>
      <p>
        You remain solely responsible for your broker account. We do not have the ability
        to withdraw funds from your broker account. Execution instructions are sent to
        your broker via your configured connection; we do not act as a broker or
        intermediary for financial transactions.
      </p>

      {/* 4. AI & Analysis Data */}
      <h2 id="ai-data">4. AI &amp; Analysis Data</h2>
      <p>
        The Platform uses AI language models to process trading analysis. Depending on
        your subscription plan:
      </p>
      <h3>4.1 Pro BYOK (Bring Your Own Key)</h3>
      <p>
        Your AI provider API key is stored encrypted at rest. Analysis requests are sent
        directly to your chosen AI provider (Anthropic Claude, OpenAI, Google Gemini, or
        a self-hosted endpoint) using your key. Your data is subject to that provider&rsquo;s
        privacy policy in addition to ours.
      </p>
      <h3>4.2 Pro Managed</h3>
      <p>
        Analysis requests are processed using a platform-managed AI key. The same
        provider data-handling considerations apply.
      </p>
      <h3>4.3 Analysis Logs</h3>
      <p>We store analysis outputs including:</p>
      <ul>
        <li>Analysis results, direction, confidence scores, and grade</li>
        <li>LLM provider and model used</li>
        <li>Processing duration and token usage (for billing and optimisation)</li>
        <li>Audit trail of applied trading rules and RAG retrieval context</li>
      </ul>
      <p>
        These logs are used to improve the Platform, debug issues, and provide you with
        your analysis history. We do not sell analysis data to third parties.
      </p>

      {/* 5. Usage Analytics */}
      <h2 id="usage-analytics">5. Usage Analytics &amp; Diagnostics</h2>
      <p>We collect operational data to maintain and improve the Platform:</p>
      <ul>
        <li>Feature usage patterns (which features are used, how frequently)</li>
        <li>Performance metrics (response times, error rates, cycle durations)</li>
        <li>Security logs (login attempts, session activity, IP addresses)</li>
        <li>Usage counters (analyses per day, execution attempts, watcher counts)</li>
      </ul>
      <p>
        This data is used for platform stability, security monitoring, capacity planning,
        and improving the user experience. It is not used for advertising.
      </p>

      {/* 6. Cookies */}
      <h2 id="cookies">6. Cookies &amp; Session Data</h2>
      <p>
        We use cookies to manage your authenticated session. For full details, see our{' '}
        <a href="/cookie-policy">Cookie Policy</a>. In summary:
      </p>
      <ul>
        <li><strong>Authentication cookies:</strong> HttpOnly, Secure cookies that maintain your login session. These are essential and cannot be disabled.</li>
        <li><strong>CSRF token cookie:</strong> A readable cookie used to protect against cross-site request forgery attacks.</li>
        <li><strong>Preference cookies:</strong> Store your theme preference (dark/light mode).</li>
      </ul>
      <p>
        We do not use third-party advertising cookies or tracking pixels.
      </p>

      {/* 7. Data Security */}
      <h2 id="security">7. Data Security</h2>
      <p>
        We implement industry-standard security measures to protect your data:
      </p>
      <ul>
        <li>All data in transit is encrypted using TLS 1.2 or higher</li>
        <li>Passwords are hashed using bcrypt with a cost factor of 12</li>
        <li>Broker credentials and API keys are encrypted at rest using AES-256</li>
        <li>Authentication uses short-lived JWT access tokens (15 minutes) with HttpOnly cookie delivery</li>
        <li>Refresh tokens are rotated on every use and scoped to the /auth path only</li>
        <li>CSRF protection is enforced on all state-changing requests using signed double-submit tokens</li>
        <li>Infrastructure is deployed on hardened Kubernetes clusters with network policies</li>
        <li>Access to production systems is restricted to authorised personnel only</li>
      </ul>
      <p>
        Despite these measures, no system is completely secure. We cannot guarantee
        absolute security and are not liable for breaches that occur despite reasonable
        precautions.
      </p>

      {/* 8. Third-Party Services */}
      <h2 id="third-parties">8. Third-Party Services</h2>
      <p>
        The Platform integrates with the following third-party services. Each has its own
        privacy policy:
      </p>
      <ul>
        <li><strong>Paddle / Lemon Squeezy:</strong> Payment processing and subscription management. They act as Merchant of Record and process your payment card data directly. We do not receive or store your card details.</li>
        <li><strong>Anthropic, OpenAI, Google:</strong> AI inference providers (when using BYOK or Managed plans). Analysis context is sent to these providers to generate trading analysis.</li>
        <li><strong>MetaAPI:</strong> MT5 broker connectivity infrastructure (when using MetaAPI connection type).</li>
        <li><strong>Cloud infrastructure providers:</strong> Hosting, storage, and compute infrastructure. Data is processed within secure cloud environments.</li>
        <li><strong>Twelve Data:</strong> Market data provider for technical analysis. No personal data is shared.</li>
      </ul>

      {/* 9. Data Retention */}
      <h2 id="retention">9. Data Retention</h2>
      <p>
        We retain your data for as long as your account is active or as needed to provide
        the service. Specifically:
      </p>
      <ul>
        <li><strong>Account data:</strong> Retained until account deletion is requested</li>
        <li><strong>Analysis history:</strong> Retained for the duration of your account</li>
        <li><strong>Trade journal:</strong> Retained until account deletion</li>
        <li><strong>Security logs:</strong> Retained for up to 90 days</li>
        <li><strong>Billing records:</strong> Retained for up to 7 years for legal and tax compliance</li>
        <li><strong>Webhook event idempotency records:</strong> Retained for 30 days</li>
      </ul>
      <p>
        Upon account deletion, we will delete or anonymise your personal data within 30
        days, except where retention is required by law.
      </p>

      {/* 10. User Rights */}
      <h2 id="user-rights">10. Your Rights</h2>
      <p>
        Depending on your jurisdiction, you may have the following rights regarding your
        personal data:
      </p>
      <ul>
        <li><strong>Access:</strong> Request a copy of the personal data we hold about you</li>
        <li><strong>Correction:</strong> Request correction of inaccurate or incomplete data</li>
        <li><strong>Deletion:</strong> Request deletion of your personal data (subject to legal retention requirements)</li>
        <li><strong>Portability:</strong> Request your data in a structured, machine-readable format</li>
        <li><strong>Objection:</strong> Object to certain processing activities</li>
        <li><strong>Restriction:</strong> Request restriction of processing in certain circumstances</li>
      </ul>
      <p>
        To exercise any of these rights, contact us at{' '}
        <a href="mailto:privacy@exoper.com">privacy@exoper.com</a>. We will respond within
        30 days. We may need to verify your identity before processing your request.
      </p>

      {/* 11. Children */}
      <h2 id="children">11. Children&rsquo;s Privacy</h2>
      <p>
        The Platform is not directed at individuals under the age of 18. We do not
        knowingly collect personal data from children. If you believe we have inadvertently
        collected data from a child, please contact us immediately and we will delete it.
      </p>

      {/* 12. Changes */}
      <h2 id="changes">12. Changes to This Policy</h2>
      <p>
        We may update this Privacy Policy from time to time. When we make material changes,
        we will notify you by email or by displaying a prominent notice on the Platform.
        The updated policy will be effective from the date stated at the top of this page.
      </p>

      {/* 13. Contact */}
      <h2 id="contact">13. Contact</h2>
      <p>
        For privacy-related enquiries, data access requests, or to report a concern:
      </p>
      <ul>
        <li>Email: <a href="mailto:privacy@exoper.com">privacy@exoper.com</a></li>
        <li>Support: <a href="/dashboard/support">Platform Support Centre</a></li>
      </ul>
    </LegalPageLayout>
  );
}
