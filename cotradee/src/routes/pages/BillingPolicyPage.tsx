import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'plans', title: '2. Subscription Plans' },
  { id: 'billing-cycles', title: '3. Billing Cycles' },
  { id: 'payment-methods', title: '4. Payment Methods' },
  { id: 'renewals', title: '5. Automatic Renewals' },
  { id: 'failed-payments', title: '6. Failed Payments' },
  { id: 'upgrades-downgrades', title: '7. Upgrades & Downgrades' },
  { id: 'taxes', title: '8. Taxes & VAT' },
  { id: 'cancellation', title: '9. Cancellation' },
  { id: 'merchant-of-record', title: '10. Merchant of Record' },
  { id: 'contact', title: '11. Contact' },
];

export default function BillingPolicyPage() {
  return (
    <LegalPageLayout
      title="Billing Policy"
      subtitle="This policy explains how Exoper subscriptions are billed, renewed, and managed. Understanding this policy helps you avoid unexpected charges."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <p>
        Exoper offers subscription-based access to its trading infrastructure platform.
        Subscriptions are billed on a recurring basis through our payment processors,
        Paddle and Lemon Squeezy. This policy explains how billing works, what to expect
        at renewal, and how to manage your subscription.
      </p>

      {/* 2. Plans */}
      <h2 id="plans">2. Subscription Plans</h2>
      <p>Exoper currently offers the following subscription tiers:</p>
      <ul>
        <li>
          <strong>Free:</strong> No charge. Limited access to core analysis features
          with usage restrictions (1 active symbol, 1 analysis per day, no automated
          execution).
        </li>
        <li>
          <strong>Pro BYOK (Bring Your Own Key):</strong> Paid subscription. Full platform
          access including unlimited symbols, unlimited analyses, automated execution,
          and trade management. Requires your own AI provider API key.
        </li>
        <li>
          <strong>Pro Managed:</strong> Paid subscription. Everything in Pro BYOK, plus
          a platform-managed AI key included. No external AI provider account required.
        </li>
      </ul>
      <p>
        Current pricing is displayed on the <a href="/pricing">Pricing page</a> and
        within the Platform. Prices are subject to change with reasonable notice.
      </p>

      {/* 3. Billing Cycles */}
      <h2 id="billing-cycles">3. Billing Cycles</h2>
      <p>
        Paid subscriptions are billed on a monthly basis. The billing cycle begins on
        the date you first subscribe and renews on the same date each month.
      </p>
      <p>
        Your subscription period and next billing date are visible in the Platform
        settings under Settings &rarr; Billing.
      </p>

      {/* 4. Payment Methods */}
      <h2 id="payment-methods">4. Payment Methods</h2>
      <p>
        Payments are processed by Paddle or Lemon Squeezy (your choice at checkout).
        Accepted payment methods include:
      </p>
      <ul>
        <li>Major credit and debit cards (Visa, Mastercard, American Express)</li>
        <li>Apple Pay and Google Pay (where available)</li>
        <li>PayPal (via Lemon Squeezy)</li>
        <li>Regional payment methods (availability varies by provider and location)</li>
      </ul>
      <p>
        Exoper does not store your payment card details. All payment data is handled
        directly by our payment processors in accordance with PCI-DSS standards.
      </p>

      {/* 5. Renewals */}
      <h2 id="renewals">5. Automatic Renewals</h2>
      <div className="legal-callout">
        <p>
          <strong>Subscriptions renew automatically at the end of each billing period.
          You will be charged the then-current subscription price unless you cancel
          before the renewal date.</strong>
        </p>
      </div>
      <p>
        We will send a renewal reminder email before each billing date. You can cancel
        at any time before the renewal date to prevent the next charge. Cancellation
        after the renewal date does not entitle you to a refund for that period.
      </p>

      {/* 6. Failed Payments */}
      <h2 id="failed-payments">6. Failed Payments &amp; Account Status</h2>
      <p>
        If a payment fails (e.g. expired card, insufficient funds, bank decline):
      </p>
      <ul>
        <li>Our payment processor will attempt to retry the charge according to their retry schedule</li>
        <li>You will receive email notifications about the failed payment</li>
        <li>Your account status will change to &ldquo;Past Due&rdquo; during the retry window</li>
        <li>You retain access to paid features during the retry window</li>
        <li>If payment is not recovered within the retry window, your subscription will be downgraded to the Free tier</li>
        <li>Your data and settings are preserved; you can resubscribe at any time</li>
      </ul>
      <p>
        To avoid service interruption, please ensure your payment method is up to date.
        You can update your payment method through the customer portal accessible from
        Settings &rarr; Billing &rarr; Manage Subscription.
      </p>

      {/* 7. Upgrades & Downgrades */}
      <h2 id="upgrades-downgrades">7. Upgrades &amp; Downgrades</h2>
      <h3>7.1 Upgrades</h3>
      <p>
        Upgrading your plan takes effect immediately. You will be charged a prorated
        amount for the remainder of the current billing period at the new plan rate.
      </p>
      <h3>7.2 Downgrades</h3>
      <p>
        Downgrading your plan takes effect at the end of the current billing period.
        You retain access to your current plan&rsquo;s features until that date.
        No refund is issued for the remaining period.
      </p>
      <h3>7.3 Plan Restrictions on Downgrade</h3>
      <p>
        When downgrading to the Free tier, the following restrictions apply immediately
        at the start of the next billing period:
      </p>
      <ul>
        <li>Active symbols are limited to 1</li>
        <li>Automated execution is disabled</li>
        <li>Automated scheduling is disabled</li>
        <li>Analyses are limited to 1 per 24 hours</li>
      </ul>

      {/* 8. Taxes */}
      <h2 id="taxes">8. Taxes &amp; VAT</h2>
      <p>
        Paddle and Lemon Squeezy act as Merchant of Record and are responsible for
        calculating, collecting, and remitting applicable taxes (including VAT, GST,
        and sales tax) in accordance with the laws of your jurisdiction.
      </p>
      <p>
        The price displayed at checkout includes applicable taxes where required by law.
        Tax amounts may vary by country. Business customers in applicable jurisdictions
        may be able to provide a VAT number to receive tax-exempt pricing.
      </p>

      {/* 9. Cancellation */}
      <h2 id="cancellation">9. Cancellation</h2>
      <p>
        You may cancel your subscription at any time:
      </p>
      <ul>
        <li>Through the Platform: Settings &rarr; Billing &rarr; Manage Subscription</li>
        <li>By contacting support at <a href="mailto:billing@exoper.com">billing@exoper.com</a></li>
      </ul>
      <p>
        Cancellation stops future billing. You retain access to paid features until the
        end of the current billing period. After that date, your account reverts to the
        Free tier. Your data and settings are preserved.
      </p>
      <p>
        Cancellation does not automatically delete your account. To delete your account,
        contact support separately.
      </p>

      {/* 10. Merchant of Record */}
      <h2 id="merchant-of-record">10. Merchant of Record</h2>
      <p>
        Exoper uses Paddle and Lemon Squeezy as its payment infrastructure providers.
        These companies act as Merchant of Record for all transactions, meaning:
      </p>
      <ul>
        <li>They appear on your bank or card statement as the merchant</li>
        <li>They are responsible for tax collection and remittance</li>
        <li>They handle payment disputes and chargebacks</li>
        <li>Their terms of service apply to the payment transaction in addition to ours</li>
      </ul>
      <p>
        Paddle: <a href="https://www.paddle.com/legal/terms" target="_blank" rel="noopener noreferrer">paddle.com/legal/terms</a><br />
        Lemon Squeezy: <a href="https://www.lemonsqueezy.com/terms" target="_blank" rel="noopener noreferrer">lemonsqueezy.com/terms</a>
      </p>

      {/* 11. Contact */}
      <h2 id="contact">11. Contact</h2>
      <p>For billing enquiries:</p>
      <ul>
        <li>Email: <a href="mailto:billing@exoper.com">billing@exoper.com</a></li>
        <li>Support: <a href="/dashboard/support">Platform Support Centre</a></li>
      </ul>
    </LegalPageLayout>
  );
}
