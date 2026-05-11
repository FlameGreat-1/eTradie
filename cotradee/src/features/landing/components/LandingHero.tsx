import { useState } from 'react';
import ImageCarousel from './ImageCarousel';
import InteractiveGridBackground from './InteractiveGridBackground';

const FEATURES = [
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
      </svg>
    ),
    publisher: 'Exoper AI',
    title: 'AI-Powered Analysis',
    description: 'Multi-timeframe technical analysis with institutional-grade order block detection and AI confidence scoring.',
    tags: ['multi-timeframe', 'order-blocks'],
  },
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
    publisher: 'Execution Engine',
    title: 'Automated Execution',
    description: 'From signal to execution in milliseconds. Dynamic position sizing, risk-managed entries, and smart TTL enforcement.',
    tags: ['low-latency', 'position-sizing'],
  },
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
    publisher: 'Dashboard',
    title: 'Live Dashboard',
    description: 'Real-time portfolio tracking, P&L visualization, trade journal, and performance analytics — all in one place.',
    tags: ['real-time', 'analytics'],
  },
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
    publisher: 'Risk Engine',
    title: 'Risk Management',
    description: 'Daily loss limits, weekly drawdown protection, correlated exposure checks, and session-aware execution guards.',
    tags: ['drawdown-guard', 'session-aware'],
  },
];

export default function LandingHero() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || submitted) return;

    // Fire-and-forget: backend handles storage + email delivery with retries.
    fetch('/api/waitlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    }).catch(() => {});

    setSubmitted(true);
    setEmail('');
    setTimeout(() => setSubmitted(false), 5000);
  };

  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden" id="hero">
      <div className="absolute top-0 left-0 w-full z-0 flex justify-center">
        <InteractiveGridBackground />
      </div>
      <div className="relative z-10 max-w-[1280px] mx-auto px-6 md:px-8">
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

          <p className="text-base sm:text-lg max-w-xl mx-auto mb-10 leading-relaxed" style={{ opacity: 0.68 }}>
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

          {/* Email-capture consent line. Required for lawful waitlist
              data collection; uses a plain <a> tag because LandingHero
              is rendered inside the landing page which already lives
              under the same react-router instance, and the existing
              header anchor pattern keeps the file dependency-free. */}
          <p className="text-[11px] mt-4 opacity-50 max-w-md mx-auto">
            By joining the waitlist you agree to our{' '}
            <a href="/privacy" className="underline decoration-[#76B900]/60 underline-offset-2 hover:opacity-100">Privacy Policy</a>.
            We use your email only to send launch updates and you can unsubscribe at any time.
          </p>
        </div>

        {/* ── Dashboard Image Carousel ────────────────────────── */}
        <div className="mb-20 md:mb-28">
          <ImageCarousel />
        </div>

        {/* ── Feature Cards Grid ──────────────────────────────── */}
        <div
          className="grid grid-cols-1 sm:grid-cols-2 gap-6"
          id="features"
        >
          {FEATURES.map((feat, i) => (
            <div key={i} className="feature-card">
              <div>
                <div className="feature-card-header">
                  <div className="feature-card-icon">{feat.icon}</div>
                  <span className="feature-card-publisher">{feat.publisher}</span>
                </div>
                <h3 className="feature-card-title">{feat.title}</h3>
                <p className="feature-card-desc">{feat.description}</p>
              </div>
              <div className="feature-card-tags">
                {feat.tags.map((tag, j) => (
                  <span key={j} className="feature-card-chip">{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}