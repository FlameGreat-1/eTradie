import { useCallback, useMemo } from 'react';
import { Twitter, Linkedin, Github } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useConsentOptional } from '@/features/consent/useConsent';
import { useAuth } from '@/features/auth';

/**
 * The footer renders three link variants:
 *
 *   internal: true   -> react-router <Link>, SPA navigation.
 *   internal: false  -> plain <a href>, regular anchor / external URL.
 *   action: 'openConsent' -> <button> wired to a feature hook.
 *
 * A discriminated union keeps the variants type-safe and forces every
 * caller to handle every case at the render site below.
 */
interface NavFooterLink {
  kind: 'nav';
  label: string;
  href: string;
  /** When true, render with react-router <Link> for SPA navigation. */
  internal?: boolean;
}

interface ActionFooterLink {
  kind: 'action';
  label: string;
  action: 'openConsent';
}

type FooterLink = NavFooterLink | ActionFooterLink;

interface FooterSection {
  title: string;
  links: FooterLink[];
}

/**
 * Build the Support column dynamically so the in-app 'Support Centre'
 * link only appears for authenticated users. Pointing guests at
 * /dashboard/support is the previous broken behaviour: ProtectedRoute
 * silently bounces them back to /landing (the 'clicking does nothing'
 * symptom). Guests instead get 'Contact Us' (public form) and
 * 'Community' (anchor link to the public-channels section on the
 * landing page).
 */
function buildSupportSection(isAuthenticated: boolean): FooterSection {
  const links: FooterLink[] = [];
  if (isAuthenticated) {
    links.push({ kind: 'nav', label: 'Support Centre', href: '/dashboard/support', internal: true });
  }
  links.push({ kind: 'nav', label: 'Contact Us', href: '/contact', internal: true });
  // The community anchor is a plain hash link so it works from any
  // page that includes the landing footer (LandingPage, ContactPage).
  // On pages without the community section the anchor is a no-op.
  links.push({ kind: 'nav', label: 'Community', href: '/landing#community', internal: true });
  // Documentation lives outside the SPA bundle. When the docs site is
  // published we'll point this at https://docs.exoper.com; until then
  // it falls back to the public Contact form so the link is never a
  // dead anchor for users who do not have an account yet.
  links.push({ kind: 'nav', label: 'System Status', href: 'https://status.exoper.com' });
  links.push({ kind: 'nav', label: 'Documentation', href: 'https://docs.exoper.com' });
  return { title: 'SUPPORT', links };
}

const PRODUCT_SECTION: FooterSection = {
  title: 'PRODUCT',
  links: [
    { kind: 'nav', label: 'AI Analysis', href: '#features' },
    { kind: 'nav', label: 'Automated Execution', href: '#features' },
    { kind: 'nav', label: 'Live Dashboard', href: '#features' },
    { kind: 'nav', label: 'Risk Management', href: '#features' },
  ],
};

const LEGAL_SECTION: FooterSection = {
  title: 'LEGAL',
  links: [
    { kind: 'nav', label: 'Terms of Service', href: '/terms', internal: true },
    { kind: 'nav', label: 'Privacy Policy', href: '/privacy', internal: true },
    { kind: 'nav', label: 'Risk Disclosure', href: '/risk-disclosure', internal: true },
    { kind: 'nav', label: 'Refund Policy', href: '/refund', internal: true },
    { kind: 'nav', label: 'Billing Policy', href: '/billing-policy', internal: true },
    { kind: 'nav', label: 'Cookie Policy', href: '/cookie', internal: true },
    { kind: 'nav', label: 'Complaints Policy', href: '/complaints', internal: true },
    { kind: 'action', label: 'Cookie Preferences', action: 'openConsent' },
  ],
};

export default function LandingFooter() {
  // useConsentOptional returns null when the footer is rendered
  // outside AppProvider (e.g. an error page, storybook snapshot,
  // maintenance page). In that case the Cookie Preferences action
  // is hidden because there is nothing to open; every other link
  // still works. PRACTICE.md #1.
  const consent = useConsentOptional();
  // Stable handler so the footer subtree does not allocate a new
  // function on every consent state change. Audit finding K.
  const openConsent = useCallback(() => {
    if (consent) consent.openPreferences();
  }, [consent]);
  // Auth state drives which Support-column entries are visible. Guests
  // do not see the in-app 'Support Centre' link because /dashboard/support
  // is gated by ProtectedRoute and would silently bounce them back to
  // /landing (the previous 'clicking does nothing' symptom).
  const { isAuthenticated } = useAuth();
  const SECTIONS = useMemo<FooterSection[]>(
    () => [PRODUCT_SECTION, buildSupportSection(isAuthenticated), LEGAL_SECTION],
    [isAuthenticated],
  );
  return (
    <footer className="landing-footer" id="landing-footer">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8 pt-16 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-16">
          {/* Brand Column */}
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-2.5">
              <img src="/assets/sidebar/icons/logo.svg" alt="Exoper" width={32} height={32} />
              <span className="text-xl font-bold tracking-tight">Exoper</span>
            </div>
            <p className="text-sm leading-relaxed max-w-xs" style={{ color: 'var(--landing-footer-text)' }}>
              Institutional-grade AI trading platform. Elevate your edge with real-time analysis and automated risk-managed execution.
            </p>
            <div className="flex items-center gap-4 mt-2">
              <a href="#" className="hover:text-[color:var(--landing-footer-text-hover)] transition-all"><Twitter size={20} /></a>
              <a href="#" className="hover:text-[color:var(--landing-footer-text-hover)] transition-all"><Linkedin size={20} /></a>
              <a href="#" className="hover:text-[color:var(--landing-footer-text-hover)] transition-all"><Github size={20} /></a>
            </div>
          </div>

          {/* Nav Columns */}
          {SECTIONS.map((section) => (
            <div key={section.title} className="flex flex-col gap-6">
              <h3 className="text-xs font-bold tracking-widest uppercase">{section.title}</h3>
              <ul className="flex flex-col gap-4">
                {section.links.map((link) => {
                  if (link.kind === 'action') {
                    // Hide the Cookie Preferences action when no
                    // ConsentProvider is mounted above. Without this
                    // guard the click handler would throw on an
                    // error page / maintenance surface; see
                    // PRACTICE.md #1 for the original incident.
                    if (link.action === 'openConsent' && !consent) {
                      return null;
                    }
                    return (
                      <li key={link.label}>
                        <button
                          type="button"
                          onClick={openConsent}
                          className="text-sm text-left hover:text-[color:var(--landing-footer-text-hover)] transition-all bg-transparent border-0 p-0 cursor-pointer"
                          style={{ color: 'inherit' }}
                        >
                          {link.label}
                        </button>
                      </li>
                    );
                  }
                  return (
                    <li key={link.label}>
                      {link.internal ? (
                        <Link
                          to={link.href}
                          className="text-sm hover:text-[color:var(--landing-footer-text-hover)] transition-all"
                        >
                          {link.label}
                        </Link>
                      ) : (
                        <a
                          href={link.href}
                          className="text-sm hover:text-[color:var(--landing-footer-text-hover)] transition-all"
                        >
                          {link.label}
                        </a>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Row */}
        <div className="pt-8 border-t border-current border-opacity-10 flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="text-xs" style={{ color: 'var(--landing-footer-text)' }}>
            © 2026 EXOPER. All rights reserved.
          </p>
          <div className="flex items-center gap-6 grayscale hover:grayscale-0 transition-all duration-500" style={{ color: 'var(--landing-footer-text)' }}>
            {/* Simulated Payment/Security Icons */}
            <span className="text-[10px] font-bold tracking-tighter border border-current px-2 py-1 rounded">STRIPE</span>
            <span className="text-[10px] font-bold tracking-tighter border border-current px-2 py-1 rounded">SECURE</span>
            <span className="text-[10px] font-bold tracking-tighter border border-current px-2 py-1 rounded">ENCRYPTED</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
