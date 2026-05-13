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
    id: 'platform-strategy',
    title: 'Platform & Strategy',
    description: 'The Exoper philosophy and operational framework.',
    items: [
      {
        id: 'what-is-exoper',
        question: 'What is Exoper?',
        answer:
          "Exoper is an institutional-grade decision-quality and execution framework for traders. It is not a signal service or a 'profit bot'. The platform retrieves the institutional rulebook (SMC, Supply & Demand, Wyckoff, DXY, COT) via RAG, runs technical and macro analysis in parallel, and synthesises a structured decision \u2014 including an explicit 'no valid setup' verdict when appropriate. The goal is discipline enforcement: helping you wait, filter, validate, and execute with structure.",
        keywords: ['overview', 'philosophy', 'value'],
      },
      {
        id: 'who-is-exoper-for',
        question: 'Who is Exoper for?',
        answer:
          'Discretionary and semi-systematic traders who understand market structure and want consistency-of-execution as their primary edge. Exoper is most useful when your bigger problem is emotional consistency rather than analysis itself.',
        keywords: ['audience', 'professional', 'beginners'],
      },
      {
        id: 'guarantees',
        question: 'Does Exoper guarantee performance?',
        answer:
          'No. Trading involves substantial risk of loss. Exoper enforces discipline and decision quality, but it does not predict the market and does not guarantee any specific outcome. All users must review the Risk Disclosure before enabling live execution.',
        keywords: ['returns', 'profit', 'risk', 'performance'],
      },
    ],
  },
  {
    id: 'intelligence-engine',
    title: 'Intelligence Engine',
    description: 'The reasoning pipeline behind every decision.',
    items: [
      {
        id: 'reasoning-pipeline',
        question: 'How does the system make decisions?',
        answer:
          "Each cycle runs technical and macro collectors in parallel, retrieves the relevant institutional rulebook from the RAG corpus, and synthesises the data against the active trading style. The result includes confluence scoring, the specific rules that validated or rejected the setup, and the invalidation levels.",
        keywords: ['pipeline', 'rag', 'llm', 'reasoning'],
      },
      {
        id: 'transparency',
        question: 'Is the reasoning transparent?',
        answer:
          'Yes. Every decision exposes the exact rules that fired, the confluence scoring, and the macro context. Transparency and explainability are core properties of the platform.',
        keywords: ['explainability', 'reasoning', 'audit'],
      },
      {
        id: 'instruments',
        question: 'Which instruments and timeframes are supported?',
        answer:
          'Exoper supports major/minor FX pairs, metals, indices, and energies offered by your connected MT5 broker. Multi-timeframe analysis spans M15 through W1 with selectable cycle intervals on Pro plans.',
        keywords: ['symbols', 'pairs', 'forex', 'timeframes'],
      },
    ],
  },
  {
    id: 'infrastructure-integration',
    title: 'Infrastructure & Integration',
    description: 'Brokers, models, and execution modes.',
    items: [
      {
        id: 'byok-vs-managed',
        question: 'Managed LLM vs. Bring Your Own Key (BYOK)',
        answer:
          'Pro users can either use our managed inference (zero setup) or "Bring Your Own Key" (OpenAI, Anthropic, or Google) to retain full control over costs, rate limits, and model choice. Both options are encrypted at rest.',
        keywords: ['byok', 'managed', 'openai', 'anthropic', 'google'],
      },
      {
        id: 'broker-connections',
        question: 'Which brokers are supported?',
        answer:
          'Any MT5-compatible broker is supported. Connection is handled either via MetaApi (cloud bridge) or a direct ZeroMQ bridge to a terminal you control. We do not hold custody of funds; your capital remains in your brokerage account.',
        keywords: ['mt5', 'metaapi', 'custody', 'broker'],
      },
      {
        id: 'demo-vs-live',
        question: 'Can I use a demo account?',
        answer:
          'Yes. We recommend validating the system on a demo account for at least one full week before enabling live automated execution.',
        keywords: ['demo', 'paper', 'sandbox'],
      },
    ],
  },
  {
    id: 'billing-compliance',
    title: 'Billing & Compliance',
    description: 'Merchant of Record, plans, and refunds.',
    items: [
      {
        id: 'payment-processor',
        question: 'Who processes my payments?',
        answer:
          'Subscriptions are processed by Paddle or Lemon Squeezy, acting as Merchant of Record. They handle global tax compliance, invoicing, and secure payment-method support. Exoper never stores card data.',
        keywords: ['paddle', 'lemon squeezy', 'tax', 'invoice'],
      },
      {
        id: 'refund-policy',
        question: 'What is your refund policy?',
        answer:
          'Refunds are reviewed case-by-case against our Refund Policy. We typically honour eligible cases such as duplicate charges or accidental renewals reported within 48 hours, provided the platform has not been used.',
        keywords: ['refund', 'money back'],
      },
      {
        id: 'plan-changes',
        question: 'How do upgrades and cancellations work?',
        answer:
          'Upgrades take effect immediately and are prorated. Cancellations and downgrades take effect at the end of the current billing cycle. You retain all paid features until the period expires.',
        keywords: ['cancel', 'upgrade', 'billing'],
      },
    ],
  },
  {
    id: 'security-data',
    title: 'Security & Data Residency',
    description: 'Protection of credentials and personal data.',
    items: [
      {
        id: 'security-posture',
        question: 'How is my account secured?',
        answer:
          'We use HttpOnly, Secure, SameSite=Strict cookies and signed CSRF tokens to prevent exfiltration. All sensitive credentials, including broker and LLM keys, are encrypted at rest.',
        keywords: ['security', 'encryption', 'cookies', 'csrf'],
      },
      {
        id: 'data-residency',
        question: 'Where is my data stored?',
        answer:
          'Account data and analysis history are stored in managed, encrypted PostgreSQL/Redis instances within the European Union. We are fully GDPR compliant regarding data export and erasure.',
        keywords: ['gdpr', 'eu', 'residency', 'storage'],
      },
    ],
  },
  {
    id: 'institutional-enterprise',
    title: 'Institutional & Enterprise',
    description: 'Solutions for firms and professional groups.',
    items: [
      {
        id: 'custom-deployments',
        question: 'Do you offer dedicated infrastructure?',
        answer:
          'Yes. Enterprise customers can request dedicated instances, custom RAG rulebooks, and private data residency. Please contact our institutional team for a custom quote.',
        keywords: ['enterprise', 'institutional', 'dedicated', 'white label'],
      },
      {
        id: 'team-access',
        question: 'Is there a team or multi-user plan?',
        answer:
          'Our Enterprise tier supports shared analysis pools and multi-seat management. This is ideal for prop firms or small groups sharing a unified trading strategy.',
        keywords: ['team', 'prop firm', 'multi-user'],
      },
      {
        id: 'support-escalation',
        question: 'What are the support escalation paths?',
        answer:
          'Pro users receive priority response times. Unresolved issues can be formally escalated via our Complaints Policy, which provides a structured timeline for review and resolution.',
        keywords: ['support', 'escalation', 'complaints'],
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
