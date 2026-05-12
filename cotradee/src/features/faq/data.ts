import type { ReactNode } from 'react';

/**
 * Typed FAQ catalogue for the public /faq page.
 *
 * Content reflects the actual platform behaviour documented in:
 *   - EXOPER.md (product philosophy, value proposition, RAG corpus)
 *   - PricingPage.tsx (Free / Pro tiers, monthly cadence)
 *   - RefundPage.tsx (eligible / non-eligible refunds)
 *   - ComplaintsPage.tsx (complaint escalation pathway)
 *   - BillingPolicyPage.tsx (Paddle / Lemon Squeezy MoR)
 *   - The BYOK / managed-LLM split documented in .env.example
 *
 * Every answer is intentionally:
 *   - precise (no marketing puff)
 *   - linked to the canonical legal / pricing page when relevant
 *   - aligned with the institutional tone EXOPER.md mandates
 *
 * IDs are stable kebab-case slugs so deep-links survive content edits
 * within a section. Removing or renaming an ID is a breaking change
 * for any third party that has linked to the FAQ.
 */

export interface FAQItem {
  /** Stable kebab-case slug used in the URL fragment. */
  id: string;
  question: string;
  /**
   * Answer rendered as a React node so individual answers can embed
   * SPA <Link>s to /pricing, /refund, /risk-disclosure, etc. without
   * importing the FAQ page itself.
   */
  answer: ReactNode;
  /**
   * Optional keyword list mixed into the client-side search index.
   * Use this to surface a Q under search terms that do not appear
   * verbatim in the question or answer text.
   */
  keywords?: string[];
}

export interface FAQCategory {
  /** Stable slug for the category itself; used by the sidebar anchors. */
  id: string;
  title: string;
  /** One-line description shown under the category heading. */
  description: string;
  items: FAQItem[];
}

/**
 * The full catalogue. Categories appear in the order declared here
 * (which is also the order on the page and in the sidebar).
 *
 * Answers are wrapped in fragments so the renderer can drop them
 * into the accordion body without additional layout markup.
 */
export const FAQ_CATEGORIES: FAQCategory[] = [
  {
    id: 'getting-started',
    title: 'Getting started',
    description: 'Your first hour on Exoper.',
    items: [
      {
        id: 'what-is-exoper',
        question: 'What is Exoper?',
        answer:
          "Exoper is an institutional-grade decision-quality and execution framework for traders. It is not a signal service or a 'profit bot'. The platform retrieves the institutional rulebook (SMC, Supply &amp; Demand, Wyckoff, DXY, COT) via RAG, runs technical and macro analysis in parallel, and synthesises a structured decision \u2014 including an explicit 'no valid setup' verdict when appropriate. The goal is discipline enforcement: helping you wait, filter, validate, reject, and execute with structure.",
        keywords: ['overview', 'what is', 'value', 'philosophy'],
      },
      {
        id: 'who-is-exoper-for',
        question: 'Who is Exoper for?',
        answer:
          'Discretionary and semi-systematic traders who already understand market structure and want consistency-of-execution as their primary edge. Exoper is most useful when your bigger problem is emotional consistency rather than analysis itself.',
        keywords: ['audience', 'beginners', 'professional'],
      },
      {
        id: 'first-steps',
        question: 'How do I start using Exoper?',
        answer:
          "Create an account, connect your MT5 broker from the dashboard (Settings &rarr; Broker Connections), and either bring your own LLM API key or upgrade to a managed plan. Run your first analysis cycle from the dashboard and review the system's reasoning before placing any trades.",
        keywords: ['onboard', 'setup', 'install'],
      },
      {
        id: 'free-vs-pro',
        question: 'What is the difference between Free and Pro?',
        answer:
          "Free includes one AI analysis per day, basic journaling, and community support. Pro unlocks unlimited analyses, automated execution and scheduling, custom cycle intervals, Telegram alerts, advanced journal analytics, and priority support. See the full comparison on the pricing page.",
        keywords: ['plans', 'tiers', 'compare', 'pricing'],
      },
    ],
  },
  {
    id: 'how-it-works',
    title: 'How Exoper works',
    description: 'The reasoning pipeline behind every decision.',
    items: [
      {
        id: 'reasoning-pipeline',
        question: 'How does Exoper actually make decisions?',
        answer:
          "Each analysis cycle runs technical and macro collectors in parallel, retrieves the relevant institutional rulebook from the RAG corpus, and asks the LLM to synthesise everything against the active trading style. The result includes explicit confluence scoring, the rules that validated or rejected the setup, the invalidation level, and a structured decision \u2014 not a free-form prediction.",
        keywords: ['pipeline', 'rag', 'llm', 'parallel', 'reasoning'],
      },
      {
        id: 'no-setup',
        question: "Why does Exoper sometimes say 'no valid setup'?",
        answer:
          "Because most of the time, there isn't one. Forcing a signal every cycle is how retail platforms generate losses. Exoper is designed to filter out marginal opportunities and surface only the trades that pass the institutional rulebook. The 'no valid setup' verdict is one of the platform's strongest trust signals.",
        keywords: ['filter', 'reject', 'discipline', 'no signal'],
      },
      {
        id: 'transparency',
        question: 'Will I see why a setup was accepted or rejected?',
        answer:
          'Yes. Every decision exposes the rules that fired, the confluence scoring, the invalidation point, and the macro context. Transparency is not an optional add-on; it is a core property of the platform.',
        keywords: ['explainability', 'reasoning', 'audit'],
      },
      {
        id: 'ai-role',
        question: 'Is Exoper an AI product?',
        answer:
          'AI is the reasoning layer inside Exoper, not the product itself. The product is structured trading infrastructure: institutional rulebook, RAG retrieval, parallel data collectors, validated execution, risk safeguards, journaling, and explainability. The LLM is one component in that stack.',
        keywords: ['ai', 'llm', 'philosophy'],
      },
      {
        id: 'instruments',
        question: 'Which instruments and timeframes are supported?',
        answer:
          'Exoper currently supports the instruments your connected MT5 broker offers, which typically includes major and minor FX pairs, metals, indices, and energies. Multi-timeframe analysis spans M15 through W1 with the active timeframe selectable from the dashboard.',
        keywords: ['symbols', 'pairs', 'forex', 'commodities', 'timeframes'],
      },
      {
        id: 'guarantees',
        question: 'Does Exoper guarantee profits?',
        answer: (
          'No. Trading involves substantial risk of loss. Exoper enforces discipline and decision quality, but it does not predict the market and does not guarantee any specific outcome. Please read the Risk Disclosure carefully before trading.'
        ),
        keywords: ['returns', 'profit', 'risk', 'warranty'],
      },
    ],
  },
  {
    id: 'plans-billing',
    title: 'Plans & billing',
    description: 'Subscriptions, refunds, and payment processing.',
    items: [
      {
        id: 'who-processes-payments',
        question: 'Who processes payments?',
        answer:
          'Subscriptions are processed by Paddle or Lemon Squeezy, who act as Merchant of Record. They handle invoicing, tax, and payment-method support. Exoper never stores card data directly.',
        keywords: ['paddle', 'lemon squeezy', 'mor', 'merchant of record', 'tax', 'vat'],
      },
      {
        id: 'cancel-subscription',
        question: 'How do I cancel my subscription?',
        answer:
          "Open Settings &rarr; Billing in the dashboard and click 'Cancel subscription'. Your plan remains active until the end of the current billing period; nothing is charged after that.",
        keywords: ['cancel', 'unsubscribe', 'stop billing'],
      },
      {
        id: 'refunds',
        question: 'Can I get a refund?',
        answer:
          "Refunds are reviewed case-by-case against the Refund Policy. We honour eligible cases such as duplicate charges and accidental renewals (when reported within 48 hours and the platform has not been used). Refunds are issued via the same payment processor used for the original charge.",
        keywords: ['refund', 'money back', 'chargeback'],
      },
      {
        id: 'failed-payment',
        question: 'My payment failed \u2014 what happens?',
        answer:
          "Paddle and Lemon Squeezy will retry the charge automatically and email you a payment-method-update link. If retries fail, your subscription is marked past-due and the platform falls back to the Free tier until the issue is resolved. You can update your payment method any time from Settings &rarr; Billing.",
        keywords: ['payment failed', 'past due', 'retry'],
      },
      {
        id: 'upgrade-downgrade',
        question: 'How do upgrades and downgrades work?',
        answer:
          'Upgrades take effect immediately and are prorated to the current billing period. Downgrades take effect at the next renewal so you keep the paid features you have already paid for.',
        keywords: ['change plan', 'switch tier'],
      },
      {
        id: 'invoices',
        question: 'Where can I find my invoices?',
        answer:
          "Every charge generates a tax-compliant invoice delivered by Paddle or Lemon Squeezy. The invoice is attached to the receipt email and is also available from your customer portal, reachable from Settings &rarr; Billing.",
        keywords: ['receipt', 'invoice', 'tax', 'vat'],
      },
    ],
  },
  {
    id: 'brokers',
    title: 'Brokers & connections',
    description: 'Bringing your trading account into Exoper.',
    items: [
      {
        id: 'which-brokers',
        question: 'Which brokers does Exoper support?',
        answer:
          'Any MT5-compatible broker. Exoper connects either via MetaApi (cloud bridge) or via a direct ZeroMQ bridge to an MT5 terminal you control. Both options are configurable from the dashboard \u2014 no env-variable editing required.',
        keywords: ['mt5', 'metaapi', 'zeromq', 'mt4'],
      },
      {
        id: 'custody-of-funds',
        question: 'Does Exoper hold my funds?',
        answer:
          'No. Exoper never takes custody of capital. Funds remain in your brokerage account at all times; Exoper only places, monitors, and closes orders on your behalf according to the rules you have configured.',
        keywords: ['custody', 'funds', 'safety'],
      },
      {
        id: 'multiple-accounts',
        question: 'Can I connect more than one trading account?',
        answer:
          "Yes \u2014 the platform is built to support multiple broker connections per user and route analyses or executions to the chosen account. The exact limit depends on your plan; see the pricing page.",
        keywords: ['multi-account', 'sub-accounts'],
      },
      {
        id: 'demo-vs-live',
        question: 'Can I connect a demo account first?',
        answer:
          'Yes \u2014 connecting a demo account is the recommended onboarding path. Validate the system on demo for at least one full week before enabling live execution.',
        keywords: ['demo', 'paper', 'sandbox'],
      },
      {
        id: 'disable-automation',
        question: 'How do I disable automated execution?',
        answer:
          'Open Settings &rarr; Broker Connections and toggle automated execution off. The platform continues to surface analyses and journal entries but never places orders until you re-enable it.',
        keywords: ['kill switch', 'disable', 'stop execution'],
      },
    ],
  },
  {
    id: 'llm-byok',
    title: 'LLM providers (BYOK)',
    description: 'Bringing your own model API key.',
    items: [
      {
        id: 'byok-what',
        question: 'What is BYOK?',
        answer:
          "BYOK stands for 'Bring Your Own Key'. You supply an LLM provider API key (currently OpenAI, Anthropic, and Google supported) and Exoper uses your account for inference. You retain control of cost, rate limits, and provider choice.",
        keywords: ['byok', 'api key', 'openai', 'anthropic', 'google'],
      },
      {
        id: 'managed-llm',
        question: 'What is the managed LLM option?',
        answer:
          'On the managed Pro tier we run inference on your behalf using our provider accounts. There is nothing to configure beyond selecting the model in the dashboard. Managed LLM is suitable for users who want zero infrastructure setup.',
        keywords: ['managed', 'hosted'],
      },
      {
        id: 'key-storage',
        question: 'How is my LLM API key stored?',
        answer:
          'BYOK keys are encrypted at rest before being persisted, and never logged, never echoed back to the dashboard, and never sent to any service other than the provider you nominated. You can rotate or delete a key any time from Settings &rarr; LLM Connections.',
        keywords: ['security', 'encryption', 'storage'],
      },
      {
        id: 'change-provider',
        question: 'Can I switch LLM providers later?',
        answer:
          'Yes \u2014 your selected provider is a per-user setting and can be changed at any time from the dashboard. Existing analyses are not retroactively re-run; new cycles use the new provider.',
        keywords: ['switch model', 'change llm'],
      },
    ],
  },
  {
    id: 'security-privacy',
    title: 'Security & privacy',
    description: 'How Exoper protects your account and data.',
    items: [
      {
        id: 'auth',
        question: 'How is my account secured?',
        answer:
          'Cookies for the access and refresh tokens are HttpOnly, Secure, and SameSite=Strict so an XSS payload cannot exfiltrate them. CSRF is enforced via signed double-submit. Optional Google OAuth is supported and account-linked from Settings.',
        keywords: ['login', 'jwt', 'cookies', 'csrf', 'oauth', 'google'],
      },
      {
        id: 'data-residency',
        question: 'Where is my data stored?',
        answer:
          'Account data, broker connections, analyses, and trade journal entries are stored on managed PostgreSQL and Redis in the European Union by default. Specific deployments may differ for enterprise customers; please contact us for details.',
        keywords: ['gdpr', 'eu', 'region', 'storage'],
      },
      {
        id: 'broker-credentials',
        question: 'Are my broker credentials encrypted?',
        answer:
          'Yes. Broker credentials are encrypted at rest. They are decrypted only in-memory when an analysis or order request is dispatched, and never logged in plain text.',
        keywords: ['mt5 password', 'security', 'encryption'],
      },
      {
        id: 'gdpr',
        question: 'How does Exoper comply with GDPR?',
        answer:
          'Cookie consent is captured with a full audit trail, retained per GDPR Article 5(1)(e) and automatically pruned after the disclosed retention window. Account deletion, data export, and consent-withdrawal requests are processed via the Privacy Policy contact channel.',
        keywords: ['gdpr', 'privacy', 'consent', 'erasure'],
      },
    ],
  },
  {
    id: 'account-data',
    title: 'Account & data',
    description: 'Managing your account, sessions, and exports.',
    items: [
      {
        id: 'change-password',
        question: 'How do I change my password?',
        answer:
          'Settings &rarr; Account &rarr; Change password. Local-login accounts can change their password directly; Google-linked accounts manage their password through Google.',
        keywords: ['password reset', 'security'],
      },
      {
        id: 'multi-session',
        question: 'Can I sign in from multiple devices?',
        answer:
          'Yes. Up to five active sessions per user are allowed by default. You can review and revoke individual sessions from Settings &rarr; Security.',
        keywords: ['sessions', 'devices', 'logout'],
      },
      {
        id: 'export-data',
        question: 'Can I export my data?',
        answer:
          'Yes \u2014 trade journal and analysis history can be exported from the dashboard in CSV / JSON. For a full account data export under GDPR Article 15 contact privacy@exoper.com.',
        keywords: ['export', 'csv', 'gdpr', 'download'],
      },
      {
        id: 'delete-account',
        question: 'How do I delete my account?',
        answer:
          'Settings &rarr; Account &rarr; Delete account permanently removes your profile and personal data after a 30-day cool-off period during which the request can be cancelled. Audit and tax records required by law are retained for the statutory minimum period.',
        keywords: ['delete', 'erasure', 'gdpr'],
      },
    ],
  },
  {
    id: 'support',
    title: 'Support',
    description: 'Talking to a human.',
    items: [
      {
        id: 'where-to-ask',
        question: 'Where can I ask a question?',
        answer:
          'Use the floating help button (bottom-right of every page), the public contact form, or open a ticket from the Support Centre once signed in. All routes feed the same ticketing backend.',
        keywords: ['contact', 'ticket', 'help'],
      },
      {
        id: 'response-time',
        question: 'What response times can I expect?',
        answer:
          "Pro tickets are prioritised and typically acknowledged within one business day. Free-tier tickets are answered as capacity permits and benefit from the community channels.",
        keywords: ['sla', 'response', 'priority'],
      },
      {
        id: 'community-channels',
        question: 'Are there community channels?',
        answer:
          "Yes \u2014 the Facebook page, Discord server, Telegram channel, and WhatsApp broadcast are linked from the Community section on the landing page. They are public discussion spaces; for account-specific issues please open a support ticket.",
        keywords: ['discord', 'telegram', 'whatsapp', 'facebook', 'community'],
      },
      {
        id: 'complaints',
        question: 'What if my issue is not resolved?',
        answer:
          'Every unresolved issue can be escalated via the Complaints Policy. The policy describes how to raise a complaint, the review process, the timelines you can expect, and the escalation path.',
        keywords: ['escalation', 'unhappy', 'dispute'],
      },
    ],
  },
];

/**
 * Convenience: a flat view of every Q&A, useful for client-side
 * search indexing. The category slug is preserved so the renderer
 * can highlight the matching section header.
 */
export interface FlatFAQItem extends FAQItem {
  categoryId: string;
  categoryTitle: string;
}

export function flattenFAQ(): FlatFAQItem[] {
  const out: FlatFAQItem[] = [];
  for (const cat of FAQ_CATEGORIES) {
    for (const item of cat.items) {
      out.push({ ...item, categoryId: cat.id, categoryTitle: cat.title });
    }
  }
  return out;
}
