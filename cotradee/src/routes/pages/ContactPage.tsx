import { memo } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen } from 'lucide-react';
import ContactForm from '@/features/support/components/ContactForm';
import CommunityLinks from '@/features/support/components/CommunityLinks';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';
import { useAuth } from '@/features/auth';
// Pulls in the .brand-icon-help mask utility so the page-hero icon
// can render the in-house helpAndFaq.svg tinted with the brand token.
import '@/features/landing/landing.css';
import '@/features/faq/faq.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';

/**
 * Public /contact page.
 *
 * Hosts the public ContactForm alongside the community-links card and
 * a compact 'already have an account?' hint that deep-links to the
 * authenticated Support Centre. Reachable by both guests and authed
 * users so anyone clicking 'Contact Us' from the landing footer or
 * a transactional email lands on a consistent surface.
 */
function ContactPage() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="landing-page">
      <ParticlesCanvas />
      <div className="landing-content">
        <LandingHeader forceScrolled />

        <main className="w-full max-w-[900px] mx-auto px-6 pt-32 pb-32">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-xs mb-10" aria-label="Breadcrumb">
            <Link
              to="/landing"
              className="transition-colors duration-150"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              Home
            </Link>
            <span style={{ color: 'var(--landing-text-faint)' }}>›</span>
            <span style={{ color: 'var(--landing-text)' }}>Contact us</span>
          </nav>

          <header className="flex flex-col items-center text-center mb-12">
            <span
              className="flex items-center justify-center w-12 h-12 rounded-full mb-4"
              style={{
                background: 'rgba(118,185,0,0.12)',
                border: '1px solid rgba(118,185,0,0.25)',
              }}
            >
              <span
                className="brand-icon-help"
                style={{ color: '#76b900', width: 22, height: 22 }}
                aria-hidden
              />
            </span>
            <h1
              className="text-3xl md:text-4xl font-bold tracking-tight mb-3"
              style={{ color: 'var(--landing-text)' }}
            >
              Contact us
            </h1>
            <p
              className="text-base max-w-xl mx-auto"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              Have a question, a bug to report, or feedback about Exoper? Send us a message and our team will get back to you.
            </p>
          </header>

          <div className="space-y-6">
            {isAuthenticated && (
              <div
                className="flex items-center justify-between gap-4 rounded-xl px-6 py-4"
                style={{
                  background: 'var(--landing-card-bg)',
                  border: '1px solid var(--landing-card-border)',
                }}
              >
                <div>
                  <p className="text-sm font-bold" style={{ color: 'var(--landing-text)' }}>
                    You're signed in
                  </p>
                  <p className="text-xs" style={{ color: 'var(--landing-text-faint)' }}>
                    Manage your existing tickets in the Support Centre.
                  </p>
                </div>
                <Link
                  to="/dashboard/support"
                  className="inline-flex items-center gap-1.5 rounded-lg px-4 h-9 text-xs font-semibold"
                  style={{ background: '#76b900', color: '#0a0a0a' }}
                >
                  Open Support Centre
                  <ArrowRight size={12} />
                </Link>
              </div>
            )}

            <div
              className="flex items-center justify-between gap-4 rounded-xl px-6 py-4"
              style={{
                background: 'var(--landing-card-bg)',
                border: '1px solid var(--landing-card-border)',
              }}
            >
              <div className="flex items-center gap-4 min-w-0">
                <span
                  className="flex items-center justify-center w-10 h-10 rounded-lg shrink-0"
                  style={{
                    background: 'rgba(118,185,0,0.1)',
                    color: '#76b900',
                  }}
                >
                  <BookOpen size={18} />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-bold" style={{ color: 'var(--landing-text)' }}>
                    Have a quick question first?
                  </p>
                  <p className="text-xs" style={{ color: 'var(--landing-text-faint)' }}>
                    Browse the FAQs — most common questions are answered there.
                  </p>
                </div>
              </div>
              <Link
                to="/faq"
                className="inline-flex items-center gap-1.5 rounded-lg border px-4 h-9 text-xs font-semibold shrink-0"
                style={{
                  borderColor: 'var(--landing-card-border)',
                  color: 'var(--landing-text)',
                  background: 'rgba(255,255,255,0.03)',
                }}
              >
                View FAQs
                <ArrowRight size={12} />
              </Link>
            </div>

            <div
              className="rounded-2xl p-8"
              style={{
                background: 'var(--landing-card-bg)',
                border: '1px solid var(--landing-card-border)',
              }}
            >
              <ContactForm
                defaultEmail={user?.email ?? ''}
                defaultName={user?.username ?? ''}
                variant="bare"
                heading="Send us a message"
              />
            </div>

            <CommunityLinks variant="bare" />

            {!isAuthenticated && (
              <p className="text-xs text-center pt-4" style={{ color: 'var(--landing-text-faint)' }}>
                Already have an account?{' '}
                <Link
                  to="/login?returnTo=/dashboard/support"
                  className="font-bold"
                  style={{ color: '#76b900' }}
                >
                  Sign in to view your tickets
                </Link>
                .
              </p>
            )}
          </div>
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}

export default memo(ContactPage);
