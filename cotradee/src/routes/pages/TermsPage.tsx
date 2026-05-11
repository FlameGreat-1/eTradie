import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'platform-nature', title: '2. Platform Nature' },
  { id: 'eligibility', title: '3. Eligibility' },
  { id: 'account', title: '4. Account' },
  { id: 'subscriptions', title: '5. Subscriptions' },
  { id: 'user-responsibilities', title: '6. User Responsibilities' },
  { id: 'automation-risks', title: '7. Automation Risks' },
  { id: 'acceptable-use', title: '8. Acceptable Use' },
  { id: 'intellectual-property', title: '9. Intellectual Property' },
  { id: 'liability', title: '10. Limitation of Liability' },
  { id: 'indemnification', title: '11. Indemnification' },
  { id: 'termination', title: '12. Termination' },
  { id: 'changes', title: '13. Changes to Terms' },
  { id: 'governing-law', title: '14. Governing Law' },
  { id: 'contact', title: '15. Contact' },
];

export default function TermsPage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      subtitle="Please read these terms carefully before using the Exoper platform. By accessing or using Exoper, you agree to be bound by these terms."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of the Exoper
        platform, including all associated software, services, APIs, dashboards, and
        infrastructure (collectively, the &ldquo;Platform&rdquo;), operated by Exoper
        (&ldquo;Exoper,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;).
      </p>
      <p>
        By creating an account, accessing the Platform, or using any feature of the service,
        you (&ldquo;User,&rdquo; &ldquo;you,&rdquo; or &ldquo;your&rdquo;) agree to these Terms
        in full. If you do not agree, you must not use the Platform.
      </p>

      {/* 2. Platform Nature */}
      <h2 id="platform-nature">2. Platform Nature &amp; No Financial Advice</h2>
      <div className="legal-callout">
        <p>
          <strong>Exoper is a structured trading infrastructure and decision-support platform.
          It does not provide financial advice, investment recommendations, or portfolio
          management services of any kind.</strong>
        </p>
      </div>
      <p>
        The Platform provides:
      </p>
      <ul>
        <li>AI-assisted technical and macro analysis tooling</li>
        <li>Automated trade execution infrastructure (when configured by the user)</li>
        <li>Risk management and trade management workflows</li>
        <li>Structured decision frameworks and institutional rule retrieval</li>
        <li>Subscription-based access to the above infrastructure</li>
      </ul>
      <p>
        Nothing on the Platform constitutes:
      </p>
      <ul>
        <li>Financial advice or investment advice within the meaning of any applicable law</li>
        <li>A recommendation to buy, sell, or hold any financial instrument</li>
        <li>A guarantee of trading profitability or positive returns</li>
        <li>A managed investment service or discretionary portfolio management</li>
      </ul>
      <p>
        All analysis outputs, signals, confidence scores, and execution decisions generated
        by the Platform are informational and analytical in nature. You remain solely
        responsible for all trading decisions and their outcomes.
      </p>

      {/* 3. Eligibility */}
      <h2 id="eligibility">3. Eligibility</h2>
      <p>To use the Platform, you must:</p>
      <ul>
        <li>Be at least 18 years of age (or the age of legal majority in your jurisdiction)</li>
        <li>Have the legal capacity to enter into binding contracts</li>
        <li>Not be prohibited from using the Platform under applicable law</li>
        <li>Agree to these Terms and our Privacy Policy</li>
      </ul>
      <p>
        The Platform is not available to residents of jurisdictions where its use would
        violate local law. You are responsible for determining whether your use of the
        Platform is lawful in your jurisdiction.
      </p>

      {/* 4. Account */}
      <h2 id="account">4. Account Registration &amp; Security</h2>
      <p>
        You must register an account to access the Platform. You agree to:
      </p>
      <ul>
        <li>Provide accurate, current, and complete registration information</li>
        <li>Maintain the security of your account credentials</li>
        <li>Notify us immediately of any unauthorised access to your account</li>
        <li>Not share your account with any third party</li>
        <li>Accept responsibility for all activity that occurs under your account</li>
      </ul>
      <p>
        We reserve the right to suspend or terminate accounts that we reasonably believe
        have been compromised, are being used fraudulently, or are in violation of these Terms.
      </p>

      {/* 5. Subscriptions */}
      <h2 id="subscriptions">5. Subscriptions &amp; Billing</h2>
      <h3>5.1 Subscription Plans</h3>
      <p>
        Exoper offers subscription-based access to the Platform. Current plans include:
      </p>
      <ul>
        <li><strong>Free:</strong> Limited access to core analysis features with usage restrictions</li>
        <li><strong>Pro BYOK (Bring Your Own Key):</strong> Full platform access using your own AI provider API key</li>
        <li><strong>Pro Managed:</strong> Full platform access with a platform-managed AI key included</li>
      </ul>
      <h3>5.2 Billing &amp; Renewals</h3>
      <p>
        Paid subscriptions are billed on a recurring basis (monthly or annually, as selected).
        Subscriptions renew automatically at the end of each billing period unless cancelled
        before the renewal date. You authorise us (via our payment processors, Paddle and
        Lemon Squeezy) to charge your payment method on each renewal date.
      </p>
      <h3>5.3 Payment Processing</h3>
      <p>
        Payments are processed by Paddle or Lemon Squeezy, who act as Merchant of Record.
        By subscribing, you also agree to their respective terms of service. Exoper does
        not store your payment card details.
      </p>
      <h3>5.4 Cancellation</h3>
      <p>
        You may cancel your subscription at any time through the Platform settings or by
        contacting support. Cancellation takes effect at the end of the current billing
        period. You retain access to paid features until that date.
      </p>
      <h3>5.5 Refunds</h3>
      <p>
        Refunds are governed by our <a href="/refund-policy">Refund Policy</a>. Trading
        losses, dissatisfaction with analysis outputs, or changes in market conditions
        do not constitute grounds for a refund.
      </p>
      <h3>5.6 Plan Changes</h3>
      <p>
        Upgrades take effect immediately. Downgrades take effect at the end of the current
        billing period. We reserve the right to modify pricing with reasonable notice.
      </p>

      {/* 6. User Responsibilities */}
      <h2 id="user-responsibilities">6. User Responsibilities</h2>
      <p>You acknowledge and agree that:</p>
      <ul>
        <li>
          <strong>You are solely responsible for all trading decisions.</strong> The Platform
          provides analytical infrastructure; it does not make trading decisions on your behalf
          without your explicit configuration and consent.
        </li>
        <li>
          <strong>You control your broker account.</strong> You are responsible for all
          activity on your connected broker account, including trades placed via the Platform.
        </li>
        <li>
          <strong>You configure execution parameters.</strong> Risk settings, position sizing,
          execution modes, and automation parameters are set by you. You accept full
          responsibility for the consequences of your configuration choices.
        </li>
        <li>
          <strong>You understand trading risk.</strong> Trading financial instruments involves
          substantial risk of loss. You should not trade with capital you cannot afford to lose.
        </li>
        <li>
          <strong>You maintain your API keys.</strong> If you use the BYOK plan, you are
          responsible for the security and validity of your AI provider API keys.
        </li>
        <li>
          <strong>You comply with applicable law.</strong> You are responsible for ensuring
          your use of the Platform complies with all laws applicable in your jurisdiction.
        </li>
      </ul>

      {/* 7. Automation Risks */}
      <h2 id="automation-risks">7. Automation Risks &amp; Infrastructure Limitations</h2>
      <div className="legal-warning">
        <p>
          <strong>Important:</strong> Automated trading systems carry inherent risks that
          differ from manual trading. You must understand these risks before enabling
          automated execution.
        </p>
      </div>
      <p>You acknowledge that:</p>
      <ul>
        <li>Automated execution may fail due to network interruptions, broker connectivity issues, or infrastructure outages</li>
        <li>Execution delays may occur between signal generation and order placement</li>
        <li>Broker execution quality, slippage, and fill prices are outside our control</li>
        <li>AI analysis outputs are probabilistic and may be incorrect</li>
        <li>Market conditions can change faster than the system can respond</li>
        <li>The Platform may experience downtime, maintenance windows, or unexpected outages</li>
        <li>Historical performance of the system does not guarantee future results</li>
      </ul>
      <p>
        Exoper is not liable for losses arising from any of the above circumstances.
        You are responsible for monitoring your automated configurations and disabling
        automation if market conditions or system behaviour are not as expected.
      </p>

      {/* 8. Acceptable Use */}
      <h2 id="acceptable-use">8. Acceptable Use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Use the Platform for any unlawful purpose or in violation of applicable regulations</li>
        <li>Attempt to reverse-engineer, decompile, or extract source code from the Platform</li>
        <li>Share, resell, or sublicense your account access to third parties</li>
        <li>Use automated scripts, bots, or scrapers against the Platform&rsquo;s APIs beyond their intended use</li>
        <li>Attempt to circumvent subscription tier restrictions or access controls</li>
        <li>Introduce malware, viruses, or malicious code into the Platform</li>
        <li>Conduct denial-of-service attacks or attempt to overload Platform infrastructure</li>
        <li>Misrepresent your identity or affiliation when using the Platform</li>
        <li>Use the Platform to manipulate markets or engage in fraudulent trading activity</li>
      </ul>
      <p>
        Violation of this section may result in immediate account suspension or termination
        without refund.
      </p>

      {/* 9. Intellectual Property */}
      <h2 id="intellectual-property">9. Intellectual Property</h2>
      <p>
        All intellectual property rights in the Platform, including but not limited to
        software, algorithms, AI models, RAG knowledge bases, trading frameworks, UI designs,
        and documentation, are owned by or licensed to Exoper.
      </p>
      <p>
        Your subscription grants you a limited, non-exclusive, non-transferable, revocable
        licence to access and use the Platform for your personal trading purposes only.
        This licence does not include the right to copy, modify, distribute, or create
        derivative works from any part of the Platform.
      </p>
      <p>
        You retain ownership of any data you provide to the Platform (broker credentials,
        trading preferences, journal entries). You grant us a limited licence to process
        this data solely to provide the service.
      </p>

      {/* 10. Limitation of Liability */}
      <h2 id="liability">10. Limitation of Liability</h2>
      <div className="legal-callout">
        <p>
          <strong>To the maximum extent permitted by applicable law, Exoper and its
          officers, directors, employees, and agents shall not be liable for any indirect,
          incidental, special, consequential, or punitive damages, including but not limited
          to trading losses, lost profits, missed trading opportunities, or data loss.</strong>
        </p>
      </div>
      <p>Specifically, Exoper is not liable for:</p>
      <ul>
        <li>Trading losses or missed profits arising from use of the Platform</li>
        <li>Losses resulting from AI analysis errors, inaccuracies, or hallucinations</li>
        <li>Losses resulting from automated execution failures, delays, or errors</li>
        <li>Losses resulting from broker connectivity issues or broker execution failures</li>
        <li>Losses resulting from Platform downtime, maintenance, or infrastructure outages</li>
        <li>Losses resulting from market volatility, liquidity gaps, or force majeure events</li>
        <li>Losses resulting from your misconfiguration of execution parameters or risk settings</li>
        <li>Losses resulting from third-party service failures (AI providers, cloud infrastructure)</li>
      </ul>
      <p>
        Where liability cannot be excluded by law, our total aggregate liability to you
        shall not exceed the amount you paid to us in the three months preceding the
        event giving rise to the claim.
      </p>

      {/* 11. Indemnification */}
      <h2 id="indemnification">11. Indemnification</h2>
      <p>
        You agree to indemnify, defend, and hold harmless Exoper and its officers,
        directors, employees, and agents from and against any claims, liabilities, damages,
        losses, and expenses (including reasonable legal fees) arising out of or in any way
        connected with:
      </p>
      <ul>
        <li>Your use of the Platform</li>
        <li>Your violation of these Terms</li>
        <li>Your violation of any applicable law or regulation</li>
        <li>Your trading activity conducted via the Platform</li>
        <li>Any third-party claim arising from your use of the Platform</li>
      </ul>

      {/* 12. Termination */}
      <h2 id="termination">12. Termination</h2>
      <p>
        We may suspend or terminate your access to the Platform at any time, with or
        without notice, if we reasonably believe you have violated these Terms, engaged
        in fraudulent activity, or pose a risk to the Platform or other users.
      </p>
      <p>
        You may terminate your account at any time by cancelling your subscription and
        requesting account deletion via the Platform settings or by contacting support.
        Upon termination, your right to access the Platform ceases immediately.
      </p>
      <p>
        Sections 2, 9, 10, 11, and 14 survive termination of these Terms.
      </p>

      {/* 13. Changes */}
      <h2 id="changes">13. Changes to These Terms</h2>
      <p>
        We may update these Terms from time to time. When we make material changes, we
        will notify you by email or by displaying a prominent notice on the Platform.
        Your continued use of the Platform after the effective date of the updated Terms
        constitutes your acceptance of the changes.
      </p>
      <p>
        If you do not agree to the updated Terms, you must stop using the Platform and
        cancel your subscription before the effective date.
      </p>

      {/* 14. Governing Law */}
      <h2 id="governing-law">14. Governing Law &amp; Dispute Resolution</h2>
      <p>
        These Terms are governed by and construed in accordance with applicable law.
        Any disputes arising under these Terms shall first be attempted to be resolved
        through good-faith negotiation. If negotiation fails, disputes shall be submitted
        to binding arbitration or the courts of competent jurisdiction.
      </p>
      <p>
        Nothing in this section prevents either party from seeking injunctive or other
        equitable relief in any court of competent jurisdiction.
      </p>

      {/* 15. Contact */}
      <h2 id="contact">15. Contact</h2>
      <p>
        If you have questions about these Terms, please contact us:
      </p>
      <ul>
        <li>Email: <a href="mailto:legal@exoper.com">legal@exoper.com</a></li>
        <li>Support: <a href="/dashboard/support">Platform Support Centre</a></li>
      </ul>
    </LegalPageLayout>
  );
}
