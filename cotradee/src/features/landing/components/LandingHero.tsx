import { useState } from 'react';
import ImageCarousel from './ImageCarousel';

const FEATURES = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
      </svg>
    ),
    title: 'AI-Powered Analysis',
    description: 'Multi-timeframe technical analysis with institutional-grade order block detection and AI confidence scoring.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
    title: 'Automated Execution',
    description: 'From signal to execution in milliseconds. Dynamic position sizing, risk-managed entries, and smart TTL enforcement.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
    title: 'Live Dashboard',
    description: 'Real-time portfolio tracking, P&L visualization, trade journal, and performance analytics — all in one place.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
    title: 'Risk Management',
    description: 'Daily loss limits, weekly drawdown protection, correlated exposure checks, and session-aware execution guards.',
  },
];

export default function LandingHero() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    // TODO: Wire to actual waitlist API
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 4000);
    setEmail('');
  };

  return (
    <section className="pt-32 pb-20 md:pt-40 md:pb-28" id="hero">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        {/* ── Headline + CTA ─────────────────────────────────── */}
        <div className="text-center max-w-4xl mx-auto mb-16 md:mb-20">
          <h1
            className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6"
            style={{
              letterSpacing: '-0.03em',
              lineHeight: 1.08,
            }}
          >
            Start Trading With AI Here.
          </h1>

          <p className="text-base sm:text-lg opacity-60 max-w-xl mx-auto mb-10 leading-relaxed">
            Exoper combines institutional-grade technical analysis with AI-powered
            execution to help you trade with precision, discipline, and confidence.
          </p>

          {/* Waitlist Form */}
          <form
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
            id="waitlist-form"
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="waitlist-input"
              required
              aria-label="Email for waitlist"
            />
            <button
              type="submit"
              className="btn-cta-brand flex-shrink-0"
              id="join-waitlist-btn"
            >
              {submitted ? (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  You're In!
                </>
              ) : (
                'Join Waitlist'
              )}
            </button>
          </form>
        </div>

        {/* ── Dashboard Image Carousel ────────────────────────── */}
        <div className="mb-20 md:mb-28">
          <ImageCarousel />
        </div>

        {/* ── Feature Cards Grid ──────────────────────────────── */}
        <div
          className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-5"
          id="features"
        >
          {FEATURES.map((feat, i) => (
            <div key={i} className="feature-card">
              <div className="feature-card-icon">{feat.icon}</div>
              <h3
                className="font-bold mb-2.5"
                style={{ fontSize: '0.95rem', letterSpacing: '-0.01em' }}
              >
                {feat.title}
              </h3>
              <p
                className="opacity-45 leading-relaxed"
                style={{ fontSize: '0.8rem', lineHeight: 1.65 }}
              >
                {feat.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
