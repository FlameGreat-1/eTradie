import { useState, useEffect } from 'react';
import { useCountdown } from '../hooks/useCountdown';

// ── Configure your pre-launch target date here ──────────────────────────
const LAUNCH_DATE = new Date('2026-07-01T00:00:00Z');

function pad(n: number): string {
  return n.toString().padStart(2, '0');
}

export default function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  const countdown = useCountdown(LAUNCH_DATE);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`landing-header ${scrolled ? 'scrolled' : ''}`}
      id="landing-header"
    >
      <div className="flex items-center justify-between h-full w-full max-w-[1280px] mx-auto px-6 md:px-8">
        {/* ── Logo (Left) ──────────────────────────────────────── */}
        <a
          href="/"
          className="flex items-center gap-2.5 select-none group"
          aria-label="Exoper Home"
        >
          <img
            src="/assets/sidebar/icons/logo.svg"
            alt="Exoper"
            width={32}
            height={32}
            className="select-none"
          />
          <span
            className="text-xl font-bold tracking-tight text-white group-hover:text-brand transition-colors duration-200"
            style={{ letterSpacing: '-0.03em' }}
          >
            Exoper
          </span>
        </a>

        {/* ── Countdown Timer (Center) ─────────────────────────── */}
        <div className="countdown-container hidden sm:flex">
          <span className="countdown-label">Pre-launch</span>

          {countdown.isExpired ? (
            <span className="text-[#76B900] font-bold text-sm tracking-wide uppercase">
              Launched!
            </span>
          ) : (
            <>
              <div className="countdown-segment">
                <span className="countdown-value">{pad(countdown.days)}</span>
                <span className="countdown-unit">Days</span>
              </div>
              <span className="countdown-sep">:</span>
              <div className="countdown-segment">
                <span className="countdown-value">{pad(countdown.hours)}</span>
                <span className="countdown-unit">Hrs</span>
              </div>
              <span className="countdown-sep">:</span>
              <div className="countdown-segment">
                <span className="countdown-value">{pad(countdown.minutes)}</span>
                <span className="countdown-unit">Min</span>
              </div>
              <span className="countdown-sep">:</span>
              <div className="countdown-segment">
                <span className="countdown-value">{pad(countdown.seconds)}</span>
                <span className="countdown-unit">Sec</span>
              </div>
            </>
          )}
        </div>

        {/* ── Get Started Button (Right) ───────────────────────── */}
        <a
          href="/login"
          className="btn-cta-outline text-sm"
          id="header-get-started"
        >
          <span style={{ color: 'var(--brand)' }}>Get Started</span>
        </a>
      </div>
    </header>
  );
}
