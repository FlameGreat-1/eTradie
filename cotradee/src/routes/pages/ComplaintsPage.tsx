import { Link } from 'react-router-dom';
import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'scope', title: '2. Scope' },
  { id: 'before-raising', title: '3. Before You Raise a Complaint' },
  { id: 'how-to-raise', title: '4. How to Raise a Complaint' },
  { id: 'what-to-include', title: '5. What to Include' },
  { id: 'response-timelines', title: '6. Response Timelines' },
  { id: 'review-process', title: '7. Review Process' },
  { id: 'escalation', title: '8. Escalation' },
  { id: 'payment-disputes', title: '9. Payment Disputes' },
  { id: 'good-faith', title: '10. Good-Faith Conduct' },
  { id: 'records', title: '11. Records & Confidentiality' },
  { id: 'contact', title: '12. Contact' },
];

export default function ComplaintsPage() {
  return (
    <LegalPageLayout
      title="Complaints Policy"
      subtitle="This policy explains how to raise a complaint about the Exoper platform, how we will review it, and the timelines you can expect."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        Exoper takes complaints seriously. We treat every complaint as an opportunity to
        improve the Platform and to maintain the trust of the users who rely on it. This
        policy explains how to raise a complaint, what information to provide, how we will
        handle it, and how to escalate if you are not satisfied with our response.
      </p>
      <p>
        This policy applies to all users of the Exoper platform (&ldquo;Platform&rdquo;)
        and complements our <Link to="/terms">Terms of Service</Link>,{' '}
        <Link to="/refund">Refund Policy</Link>, and <Link to="/billing-policy">Billing Policy</Link>.
      </p>

      {/* 2. Scope */}
      <h2 id="scope">2. Scope</h2>
      <p>This policy covers complaints relating to:</p>
      <ul>
        <li>Platform availability, performance, or technical defects</li>
        <li>Account access, authentication, or security concerns</li>
        <li>Billing, subscription, renewal, or refund matters</li>
        <li>Data, privacy, or cookie-handling concerns</li>
        <li>Support quality or response times</li>
        <li>Conduct of staff or automated communications</li>
        <li>Other matters relating to your use of the Platform</li>
      </ul>
      <div className="legal-callout">
        <p>
          <strong>This policy does not cover trading outcomes.</strong> Losses, missed
          opportunities, or dissatisfaction with analysis outputs are addressed by our{' '}
          <Link to="/risk-disclosure">Risk Disclosure</Link> and{' '}
          <Link to="/terms">Terms of Service</Link>. Trading outcomes are the responsibility of
          the user and are not within the scope of this complaints process.
        </p>
      </div>

      {/* 3. Before Raising */}
      <h2 id="before-raising">3. Before You Raise a Complaint</h2>
      <p>
        Many issues can be resolved quickly through the standard support channel. Before
        raising a formal complaint we encourage you to:
      </p>
      <ul>
        <li>
          Check the <Link to="/dashboard/support">Platform Support Centre</Link> for guidance
          on common issues.
        </li>
        <li>
          Review the relevant policy (for example, the <Link to="/refund">Refund Policy</Link>{' '}
          for billing matters) so your request can be processed under the correct framework.
        </li>
        <li>
          Provide our support team with a reasonable opportunity to resolve the issue.
        </li>
      </ul>
      <p>
        If you have already exhausted normal support channels, or if your concern is
        serious in nature, please proceed to raise a formal complaint.
      </p>

      {/* 4. How to Raise */}
      <h2 id="how-to-raise">4. How to Raise a Complaint</h2>
      <p>You can raise a formal complaint through any of the following channels:</p>
      <ul>
        <li>
          <strong>Email:</strong>{' '}
          <a href="mailto:support@exoper.com">support@exoper.com</a> with the subject line
          beginning &ldquo;Complaint:&rdquo;.
        </li>
        <li>
          <strong>Platform Support Centre:</strong>{' '}
          <Link to="/dashboard/support">/dashboard/support</Link>, selecting&nbsp;
          &ldquo;File a complaint&rdquo;.
        </li>
        <li>
          <strong>Billing-specific complaints:</strong>{' '}
          <a href="mailto:billing@exoper.com">billing@exoper.com</a>.
        </li>
        <li>
          <strong>Privacy or data-protection complaints:</strong>{' '}
          <a href="mailto:privacy@exoper.com">privacy@exoper.com</a>.
        </li>
      </ul>

      {/* 5. What to Include */}
      <h2 id="what-to-include">5. What to Include</h2>
      <p>To help us review your complaint efficiently, please include:</p>
      <ul>
        <li>The email address associated with your Exoper account</li>
        <li>A clear description of the issue and the impact on you</li>
        <li>The date and approximate time the issue occurred</li>
        <li>
          Any relevant identifiers (transaction ID, invoice number, support ticket
          reference, trade or analysis identifier)
        </li>
        <li>Steps already taken to resolve the issue</li>
        <li>The outcome you would like to see</li>
        <li>Any supporting evidence (screenshots, error messages, correspondence)</li>
      </ul>
      <p>
        Providing complete information at the outset significantly reduces the time taken
        to resolve your complaint.
      </p>

      {/* 6. Response Timelines */}
      <h2 id="response-timelines">6. Response Timelines</h2>
      <p>We aim to handle complaints within the following timelines:</p>
      <ul>
        <li>
          <strong>Acknowledgement:</strong> within <strong>2 business days</strong> of
          receipt.
        </li>
        <li>
          <strong>Initial substantive response:</strong> within{' '}
          <strong>7 business days</strong> of acknowledgement.
        </li>
        <li>
          <strong>Final resolution:</strong> within <strong>30 calendar days</strong> of
          receipt, where reasonably possible.
        </li>
      </ul>
      <p>
        Complex complaints (for example those requiring forensic investigation, third-party
        provider involvement, or cross-team review) may take longer. In that case we will
        keep you informed of progress and provide an updated estimate.
      </p>

      {/* 7. Review Process */}
      <h2 id="review-process">7. Review Process</h2>
      <p>Every formal complaint follows the same structured review:</p>
      <ol>
        <li>
          <strong>Receipt &amp; logging</strong> — the complaint is logged in our internal
          complaints register with a unique reference.
        </li>
        <li>
          <strong>Acknowledgement</strong> — you receive an acknowledgement with the
          reference number and the name of the team handling your case.
        </li>
        <li>
          <strong>Investigation</strong> — relevant logs, account history, payment records,
          and supporting evidence are reviewed by the appropriate team.
        </li>
        <li>
          <strong>Determination</strong> — a decision is made on the merits, including
          remediation where appropriate.
        </li>
        <li>
          <strong>Communication of outcome</strong> — you receive a written response
          explaining the outcome, the reasons, and any next steps.
        </li>
        <li>
          <strong>Closure</strong> — the complaint is closed in the register. You may
          reopen it within 14 days if you have new information.
        </li>
      </ol>

      {/* 8. Escalation */}
      <h2 id="escalation">8. Escalation</h2>
      <p>
        If you are not satisfied with the outcome of your complaint, you may request an
        escalation. Escalation requests must be submitted within <strong>14 days</strong>{' '}
        of receiving our final response and must explain why you believe the outcome should
        be reconsidered.
      </p>
      <p>
        Escalations are reviewed by a separate, more senior reviewer who was not involved
        in the original determination. We aim to provide an escalation response within{' '}
        <strong>14 business days</strong>.
      </p>
      <p>
        The escalation review is the final stage of our internal complaints process.
      </p>

      {/* 9. Payment Disputes */}
      <h2 id="payment-disputes">9. Payment Disputes &amp; External Escalation</h2>
      <p>
        Payments on the Platform are processed by Paddle or Lemon Squeezy, who act as
        Merchant of Record. For unresolved payment-related complaints, you may also contact
        the relevant payment processor directly through their support channels.
      </p>
      <p>
        Where required by law, you may have additional rights to refer disputes to a
        consumer protection authority or alternative dispute resolution body in your
        jurisdiction. Nothing in this policy limits any statutory rights you may have.
      </p>
      <div className="legal-warning">
        <p>
          <strong>Please contact us before initiating a chargeback with your bank or card
          issuer.</strong> Most billing complaints can be resolved faster through our
          support process. See our <Link to="/refund">Refund Policy</Link> for further detail.
        </p>
      </div>

      {/* 10. Good Faith */}
      <h2 id="good-faith">10. Good-Faith Conduct</h2>
      <p>
        We handle every complaint in good faith and expect the same from complainants.
        Abusive, threatening, or repeatedly frivolous communications may result in
        restrictions on the channels through which we accept further correspondence, in
        line with our <Link to="/terms">Terms of Service</Link>.
      </p>
      <p>
        Raising a complaint will not, in itself, adversely affect your account or your
        access to the Platform.
      </p>

      {/* 11. Records */}
      <h2 id="records">11. Records &amp; Confidentiality</h2>
      <p>
        Complaint records are retained for the period necessary to comply with our legal,
        regulatory, and operational obligations, and are handled in accordance with our{' '}
        <Link to="/privacy">Privacy Policy</Link>. Personal data contained in a complaint is
        accessed only by personnel who need it to resolve the matter.
      </p>

      {/* 12. Contact */}
      <h2 id="contact">12. Contact</h2>
      <p>To raise a complaint or follow up on an existing case:</p>
      <ul>
        <li>General: <a href="mailto:support@exoper.com">support@exoper.com</a></li>
        <li>Billing: <a href="mailto:billing@exoper.com">billing@exoper.com</a></li>
        <li>Privacy: <a href="mailto:privacy@exoper.com">privacy@exoper.com</a></li>
        <li>Support Centre: <Link to="/dashboard/support">Platform Support Centre</Link></li>
      </ul>
    </LegalPageLayout>
  );
}
