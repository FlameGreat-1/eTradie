import { useState, useEffect } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { useTheme } from '@/providers/ThemeProvider';

// ── Configure your pre-launch target date here ──────────────────────────
const LAUNCH_DATE = new Date('2026-07-01T00:00:00Z');

function pad(n: number): string {
  return n.toString().padStart(2, '0');
}

export default function LandingHeader({ forceScrolled = false }: { forceScrolled?: boolean }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const countdown = useCountdown(LAUNCH_DATE);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  const isLight = theme === 'light';

  return (
    <>
      <header
        className={`landing-header ${scrolled || forceScrolled ? 'scrolled' : ''}`}
        id="landing-header"
      >
      <div className="flex items-center justify-between h-full w-full max-w-[1280px] mx-auto px-6 md:px-8">
        {/* ── Left Section (Logo & Nav) ─────────────────────────── */}
        <div className="flex items-center gap-8">
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

          {/* Desktop Nav Links (Left-aligned) */}
          <nav className="hidden md:flex items-center gap-6 mt-[2px]">
            <div className="w-[1px] h-4 bg-slate-300 dark:bg-slate-700"></div>
            <a
              href="#process-flow"
              className="text-sm font-medium px-3 py-1.5 rounded-full bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors duration-200"
              style={{ color: 'var(--landing-text)' }}
            >
              Process
            </a>
            <a
              href="/pricing"
              className="text-sm font-medium px-3 py-1.5 rounded-full bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors duration-200"
              style={{ color: 'var(--landing-text)' }}
            >
              Pricing
            </a>
          </nav>
        </div>

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

        {/* ── Auth Buttons (Desktop) ───────────────────────────── */}
        <div className="hidden md:flex items-center gap-4">

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
            className="btn-cta-brand text-sm"
            id="header-join-waitlist"
          >
            Start Trading
          </a>
        </div>

          {/* ── Mobile Menu Toggle ───────────────────────────────── */}
          <div className="flex md:hidden items-center gap-3">
            <button
              onClick={toggleTheme}
              className="w-9 h-9 flex items-center justify-center rounded-lg border transition-all duration-200"
              style={{ 
                color: 'var(--landing-text)',
                borderColor: 'var(--landing-card-border)',
                background: 'var(--landing-btn-outline-bg)'
              }}
              aria-label="Toggle Theme"
            >
              {isLight ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              )}
            </button>
            
            <button 
              className="w-9 h-9 flex items-center justify-center rounded-lg border transition-all duration-200"
              style={{ 
                color: 'var(--landing-text)',
                borderColor: 'var(--landing-card-border)',
                background: 'var(--landing-btn-outline-bg)'
              }}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Mobile Menu"
            >
              {mobileMenuOpen ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* ── Mobile Backdrop ──────────────────────────────────── */}
      <div 
        className={`md:hidden fixed inset-0 z-[90] transition-opacity duration-300 ${
          mobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        style={{ background: 'rgba(0, 0, 0, 0.5)' }}
        onClick={() => setMobileMenuOpen(false)}
        aria-hidden="true"
      />

      {/* ── Mobile Dropdown Card ──────────────────────────────── */}
      <div 
        className={`md:hidden fixed top-[76px] left-4 right-4 z-[100] transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] origin-top ${
          mobileMenuOpen ? 'opacity-100 pointer-events-auto scale-100 translate-y-0' : 'opacity-0 pointer-events-none scale-[0.97] -translate-y-3'
        }`}
        style={{ 
          background: isLight ? '#f8f9fa' : '#111111',
          backgroundImage: isLight ? 'none' : 'linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0) 100%)',
          border: isLight ? '1px solid rgba(0,0,0,0.12)' : '1px solid rgba(255,255,255,0.08)',
          borderRadius: '24px',
          padding: '24px',
          boxShadow: isLight
            ? '0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.03)'
            : '0 0 0 1px rgba(255,255,255,0.02), 0 8px 24px rgba(0,0,0,0.35)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          
          {/* Process */}
          <a 
            href="#process-flow"
            onClick={() => setMobileMenuOpen(false)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              borderRadius: '14px',
              color: 'var(--landing-text)',
              textDecoration: 'none',
              transition: 'background 180ms ease',
            }}
            onMouseOver={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.04)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              <span style={{ fontSize: '15px', fontWeight: 600 }}>Process</span>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.35 }}><path d="m9 18 6-6-6-6"/></svg>
          </a>

          {/* Pricing */}
          <a
            href="/pricing"
            onClick={() => setMobileMenuOpen(false)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              borderRadius: '14px',
              color: 'var(--landing-text)',
              textDecoration: 'none',
              transition: 'background 180ms ease',
            }}
            onMouseOver={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.04)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 18V6"/></svg>
              <span style={{ fontSize: '15px', fontWeight: 600 }}>Pricing</span>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.35 }}><path d="m9 18 6-6-6-6"/></svg>
          </a>

          {/* Sign In */}
          <a 
            href="/login"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              borderRadius: '14px',
              color: 'var(--landing-text)',
              textDecoration: 'none',
              transition: 'background 180ms ease',
            }}
            onMouseOver={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.04)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#76B900" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
              <span style={{ fontSize: '15px', fontWeight: 600 }}>Sign In</span>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.35 }}><path d="m9 18 6-6-6-6"/></svg>
          </a>

          {/* Divider */}
          <div style={{ height: '1px', background: isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)' }} />

          {/* Start Trading */}
          <a 
            href="/register"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              borderRadius: '14px',
              color: 'var(--landing-text)',
              textDecoration: 'none',
              transition: 'background 180ms ease',
            }}
            onMouseOver={(e) => e.currentTarget.style.background = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.04)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <img src="/assets/sidebar/icons/logo.svg" alt="Exoper" width="18" height="18" style={{ opacity: 0.9 }} />
              <span style={{ fontSize: '15px', fontWeight: 600 }}>Start Trading</span>
            </div>
            <span 
              className="feature-card-chip" 
              style={{ height: '28px', fontSize: '11px', padding: '0 10px', marginRight: '-4px' }}
            >
              Join Now
            </span>
          </a>

        </div>
      </div>
    </>
  );
}

