import { memo } from 'react';
import { Link } from 'react-router-dom';
import { LifeBuoy, ArrowRight } from 'lucide-react';
import ContactForm from '@/features/support/components/ContactForm';
import CommunityLinks from '@/features/support/components/CommunityLinks';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';
import { useAuth } from '@/features/auth';

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
    <div className="min-h-screen flex flex-col bg-app">
      <LandingHeader />

      <main className="flex-1">
        <section className="max-w-4xl mx-auto px-6 md:px-8 py-12 md:py-16">
          <header className="flex flex-col items-center text-center mb-10">
            <span className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-soft text-brand mb-4">
              <LifeBuoy size={22} />
            </span>
            <h1 className="text-2xl md:text-3xl font-bold text-content mb-2 tracking-tight">
              Contact us
            </h1>
            <p className="text-sm text-content-muted max-w-xl">
              Have a question, a bug to report, or feedback about Exoper? Send us a message and our team will get back to you.
            </p>
          </header>

          {isAuthenticated && (
            <div className="mb-6 flex items-center justify-between gap-4 rounded-xl border border-border bg-surface-1 px-4 py-3">
              <div>
                <p className="text-xs font-semibold text-content">You're signed in</p>
                <p className="text-[11px] text-content-muted">
                  Manage your existing tickets in the Support Centre.
                </p>
              </div>
              <Link
                to="/dashboard/support"
                className="inline-flex items-center gap-1.5 rounded-md bg-brand px-3 h-8 text-xs font-semibold
                           text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
              >
                Open Support Centre
                <ArrowRight size={12} />
              </Link>
            </div>
          )}

          <ContactForm
            defaultEmail={user?.email ?? ''}
            defaultName={user?.username ?? ''}
            heading="Send us a message"
          />

          <div className="mt-6">
            <CommunityLinks />
          </div>

          {!isAuthenticated && (
            <p className="text-[11px] text-content-muted text-center mt-8">
              Already have an account?{' '}
              <Link to="/login?returnTo=/dashboard/support" className="text-brand hover:underline font-semibold">
                Sign in to view your tickets
              </Link>
              .
            </p>
          )}
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}

export default memo(ContactPage);
