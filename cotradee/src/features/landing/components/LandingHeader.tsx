import { useState, useEffect } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { useTheme } from '@/providers/ThemeProvider';

// ── Configure your pre-launch target date here ──────────────────────────
const LAUNCH_DATE = new Date('2026-07-01T00:00:00Z');

function pad(n: number): string {
  return n.toString().padStart(2, '0');
}

export default function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  const countdown = useCountdown(LAUNCH_DATE);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const isLight = theme === 'light';

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
            className="text-xl font-bold tracking-tight group-hover:text-brand transition-colors duration-200"
            style={{ letterSpacing: '-0.03em', color: 'var(--landing-text)' }}
          >
            Exoper
          </span>
        </a>

        {/* ── Countdown Timer (Center) ─────────────────────────── */}
        <div className="countdown-container hidden lg:flex">
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

        {/* ── Auth Buttons (Right) ───────────────────────────── */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-9 h-9 flex items-center justify-center rounded-lg border transition-all duration-200 hover:bg-current hover:bg-opacity-[0.08]"
            style={{ 
              color: 'var(--landing-text)',
              borderColor: 'var(--landing-card-border)',
              background: 'var(--landing-btn-outline-bg)'
            }}
            aria-label="Toggle Theme"
          >
            {isLight ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            )}
          </button>

          <a
            href="/login"
            className="text-sm font-medium opacity-70 hover:opacity-100 transition-opacity duration-200"
            style={{ color: 'var(--landing-text)' }}
          >
            Sign In
          </a>
          <a
            href="/register"
            className="btn-cta-outline text-sm"
            id="header-start-trading"
          >
            <span style={{ color: 'var(--brand)' }}>Start Trading</span>
          </a>
        </div>
      </div>
    </header>
  );
}
