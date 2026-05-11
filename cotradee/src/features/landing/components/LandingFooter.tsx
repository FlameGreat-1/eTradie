import { Twitter, Linkedin, Github } from 'lucide-react';
import { Link } from 'react-router-dom';

interface FooterLink {
  label: string;
  href: string;
  /** When true, render with react-router <Link> for SPA navigation. */
  internal?: boolean;
}

interface FooterSection {
  title: string;
  links: FooterLink[];
}

const SECTIONS: FooterSection[] = [
  {
    title: 'PRODUCT',
    links: [
      { label: 'AI Analysis', href: '#features' },
      { label: 'Automated Execution', href: '#features' },
      { label: 'Live Dashboard', href: '#features' },
      { label: 'Risk Management', href: '#features' },
    ],
  },
  {
    title: 'SUPPORT',
    links: [
      { label: 'Documentation', href: '#' },
      { label: 'Help Center', href: '#' },
      { label: 'Contact Us', href: '#' },
      { label: 'System Status', href: '#' },
    ],
  },
  {
    title: 'LEGAL',
    links: [
      { label: 'Terms of Service', href: '/terms', internal: true },
      { label: 'Privacy Policy', href: '/privacy', internal: true },
      { label: 'Risk Disclosure', href: '/risk-disclosure', internal: true },
      { label: 'Refund Policy', href: '/refund', internal: true },
      { label: 'Billing Policy', href: '/billing-policy', internal: true },
      { label: 'Cookie Policy', href: '/cookie', internal: true },
      { label: 'Complaints Policy', href: '/complaints', internal: true },
    ],
  },
];

export default function LandingFooter() {
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
                {section.links.map((link) => (
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
                ))}
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
