import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import '@/features/landing/landing.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';

interface Section {
  id: string;
  title: string;
}

interface LegalPageLayoutProps {
  title: string;
  subtitle: string;
  effectiveDate: string;
  lastUpdated: string;
  sections: Section[];
  children: ReactNode;
}

/**
 * LegalPageLayout is the shared chrome for every Exoper legal document.
 *
 * It reuses the exact same visual world as PricingPage and ProcessPage:
 * landing.css, ParticlesCanvas, LandingHeader, LandingFooter. The
 * document itself is rendered in a two-column layout on desktop:
 * a sticky table-of-contents sidebar on the left and the document
 * body on the right. On mobile both collapse to a single column.
 *
 * The institutional tone (minimal, sharp, structured) matches the
 * EXOPER.md design philosophy throughout.
 */
export default function LegalPageLayout({
  title,
  subtitle,
  effectiveDate,
  lastUpdated,
  sections,
  children,
}: LegalPageLayoutProps) {
  return (
    <div className="landing-page">
      <ParticlesCanvas />
      <div className="landing-content">
        <LandingHeader forceScrolled />

        <main className="w-full max-w-[1100px] mx-auto px-6 pt-32 pb-32">
          {/* ── Breadcrumb ─────────────────────────────────────── */}
          <nav className="flex items-center gap-2 text-xs mb-10" aria-label="Breadcrumb">
            <Link
              to="/landing"
              className="transition-colors duration-150"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              Home
            </Link>
            <span style={{ color: 'var(--landing-text-faint)' }}>›</span>
            <span style={{ color: 'var(--landing-text)' }}>{title}</span>
          </nav>

          {/* ── Document Header ────────────────────────────────── */}
          <div className="mb-12">
            <div className="inline-flex items-center gap-2 mb-4">
              <span
                className="text-[10px] font-bold uppercase tracking-[0.25em] px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(118,185,0,0.12)',
                  color: '#76b900',
                  border: '1px solid rgba(118,185,0,0.25)',
                }}
              >
                Legal Document
              </span>
            </div>
            <h1
              className="text-3xl md:text-4xl font-bold tracking-tight mb-3"
              style={{ color: 'var(--landing-text)' }}
            >
              {title}
            </h1>
            <p className="text-base mb-6" style={{ color: 'var(--landing-text-faint)' }}>
              {subtitle}
            </p>
            <div
              className="flex flex-wrap items-center gap-6 text-xs"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              <span>
                <span className="font-semibold" style={{ color: 'var(--landing-text)' }}>Effective:</span>{' '}
                {effectiveDate}
              </span>
              <span>
                <span className="font-semibold" style={{ color: 'var(--landing-text)' }}>Last updated:</span>{' '}
                {lastUpdated}
              </span>
            </div>
          </div>

          {/* ── Divider ───────────────────────────────────────── */}
          <div
            className="w-full h-[1px] mb-12"
            style={{
              background:
                'linear-gradient(to right, transparent, var(--landing-card-border), transparent)',
            }}
          />

          {/* ── Two-column layout ─────────────────────────────── */}
          <div className="flex flex-col lg:flex-row gap-12">
            {/* Sticky ToC sidebar */}
            <aside className="lg:w-56 flex-shrink-0">
              <div className="lg:sticky lg:top-28">
                <p
                  className="text-[10px] font-bold uppercase tracking-[0.25em] mb-4"
                  style={{ color: 'var(--landing-text-faint)' }}
                >
                  Contents
                </p>
                <nav className="flex flex-col gap-1" aria-label="Table of contents">
                  {sections.map((s) => (
                    <a
                      key={s.id}
                      href={`#${s.id}`}
                      className="text-sm py-1.5 px-3 rounded-lg transition-colors duration-150 block"
                      style={{ color: 'var(--landing-text-faint)' }}
                      onMouseOver={(e) => {
                        (e.currentTarget as HTMLElement).style.color = 'var(--landing-text)';
                        (e.currentTarget as HTMLElement).style.background =
                          'var(--landing-card-bg)';
                      }}
                      onMouseOut={(e) => {
                        (e.currentTarget as HTMLElement).style.color = 'var(--landing-text-faint)';
                        (e.currentTarget as HTMLElement).style.background = 'transparent';
                      }}
                    >
                      {s.title}
                    </a>
                  ))}
                </nav>
              </div>
            </aside>

            {/* Document body */}
            <article
              className="flex-1 min-w-0 legal-body"
              style={{ color: 'var(--landing-text)' }}
            >
              {children}
            </article>
          </div>
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}
