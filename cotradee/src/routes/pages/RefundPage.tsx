import { Link } from 'react-router-dom';
import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'eligible-refunds', title: '2. Eligible Refunds' },
  { id: 'non-refundable', title: '3. Non-Refundable' },
  { id: 'process', title: '4. Refund Process' },
  { id: 'chargebacks', title: '5. Chargebacks' },
  { id: 'cancellation', title: '6. Cancellation' },
  { id: 'contact', title: '7. Contact' },
];

export default function RefundPage() {
  return (
    <LegalPageLayout
      title="Refund Policy"
      subtitle="This policy explains when refunds are available, how to request them, and what circumstances do not qualify for a refund."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        Exoper operates a controlled, policy-based refund process. We do not offer
        automatic refunds. Each refund request is reviewed individually against the
        criteria set out in this policy.
      </p>
      <p>
        Payments are processed by Paddle or Lemon Squeezy, who act as Merchant of Record.
        Refunds are issued through the same payment processor used for the original charge.
      </p>

      {/* 2. Eligible Refunds */}
      <h2 id="eligible-refunds">2. Eligible Refund Circumstances</h2>
      <p>
        A refund may be issued in the following circumstances:
      </p>
      <ul>
        <li>
          <strong>Duplicate charge:</strong> You were charged more than once for the same
          subscription period due to a billing system error.
        </li>
        <li>
          <strong>Accidental renewal:</strong> Your subscription renewed automatically and
          you contact us within <strong>48 hours</strong> of the renewal charge, have not
          used the Platform during that period, and have not previously requested a refund
          for an accidental renewal.
        </li>
        <li>
          <strong>Technical failure:</strong> A verified technical failure on our side
          prevented you from accessing the Platform for a material portion of your
          subscription period, and the issue was not resolved within a reasonable timeframe.
        </li>
        <li>
          <strong>Billing error:</strong> You were charged an incorrect amount due to a
          pricing or billing system error on our part.
        </li>
      </ul>
      <p>
        All refund requests are subject to review and approval. Meeting one of the above
        criteria does not guarantee a refund; we reserve the right to decline requests
        that do not meet the full criteria or where abuse is suspected.
      </p>

      {/* 3. Non-Refundable */}
      <h2 id="non-refundable">3. Non-Refundable Circumstances</h2>
      <div className="legal-callout">
        <p>
          <strong>The following circumstances do not qualify for a refund under any
          circumstances.</strong>
        </p>
      </div>
      <ul>
        <li>
          <strong>Trading losses:</strong> Losses incurred while trading using the Platform,
          regardless of the cause, do not qualify for a refund. Trading involves inherent
          risk and Exoper does not guarantee profitable outcomes.
        </li>
        <li>
          <strong>Dissatisfaction with analysis outputs:</strong> Disagreement with the
          Platform&rsquo;s analysis, signals, or recommendations does not qualify for a refund.
        </li>
        <li>
          <strong>Change of mind:</strong> Deciding you no longer want to use the Platform
          after a subscription period has begun does not qualify for a refund.
        </li>
        <li>
          <strong>Partial period use:</strong> If you use the Platform for any portion of
          a billing period, that period is not refundable.
        </li>
        <li>
          <strong>Account suspension for Terms violation:</strong> If your account is
          suspended or terminated due to a violation of our Terms of Service, no refund
          will be issued.
        </li>
        <li>
          <strong>Market conditions:</strong> Adverse market conditions, missed trading
          opportunities, or broker execution issues do not qualify for a refund.
        </li>
        <li>
          <strong>AI analysis inaccuracies:</strong> Losses or dissatisfaction arising
          from AI analysis outputs do not qualify for a refund.
        </li>
        <li>
          <strong>Requests outside the eligible window:</strong> Refund requests submitted
          more than 48 hours after the charge (for accidental renewals) or more than 14
          days after the charge (for other eligible circumstances) will not be considered.
        </li>
      </ul>

      {/* 4. Process */}
      <h2 id="process">4. Refund Request Process</h2>
      <p>To request a refund:</p>
      <ol>
        <li>
          Contact us at <a href="mailto:billing@exoper.com">billing@exoper.com</a> or
          via the <Link to="/dashboard/support">Platform Support Centre</Link>.
        </li>
        <li>
          Include your account email address, the date of the charge, the amount charged,
          and a clear description of the reason for your request.
        </li>
        <li>
          We will acknowledge your request within 2 business days and provide a decision
          within 7 business days.
        </li>
        <li>
          If approved, refunds are processed through the original payment method and
          typically appear within 5–10 business days depending on your bank or card issuer.
        </li>
      </ol>
      <p>
        We may request additional information to verify your identity or the circumstances
        of your request.
      </p>

      {/* 5. Chargebacks */}
      <h2 id="chargebacks">5. Chargebacks</h2>
      <p>
        We strongly encourage you to contact us before initiating a chargeback with your
        bank or card issuer. Most billing disputes can be resolved quickly through our
        support process.
      </p>
      <p>
        Initiating a chargeback without first contacting us may result in:
      </p>
      <ul>
        <li>Immediate suspension of your account pending investigation</li>
        <li>Permanent account termination if the chargeback is found to be fraudulent or unjustified</li>
        <li>Referral to our payment processor&rsquo;s dispute resolution process</li>
      </ul>
      <p>
        Fraudulent chargebacks may be reported to relevant authorities.
      </p>

      {/* 6. Cancellation */}
      <h2 id="cancellation">6. Cancellation vs. Refund</h2>
      <p>
        Cancelling your subscription and requesting a refund are different actions:
      </p>
      <ul>
        <li>
          <strong>Cancellation</strong> stops future billing. You retain access to paid
          features until the end of the current billing period. No refund is issued for
          the remaining period.
        </li>
        <li>
          <strong>Refund</strong> returns money already charged, subject to the criteria
          in this policy.
        </li>
      </ul>
      <p>
        You can cancel your subscription at any time through the Platform settings
        (Settings &rarr; Billing &rarr; Manage Subscription) or by contacting support.
      </p>

      {/* 7. Contact */}
      <h2 id="contact">7. Contact</h2>
      <p>For refund requests or billing enquiries:</p>
      <ul>
        <li>Email: <a href="mailto:billing@exoper.com">billing@exoper.com</a></li>
        <li>Support: <Link to="/dashboard/support">Platform Support Centre</Link></li>
      </ul>
    </LegalPageLayout>
  );
}
