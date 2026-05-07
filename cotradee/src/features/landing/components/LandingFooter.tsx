const FOOTER_LINKS = [
  { label: 'Terms of Use', href: '/terms' },
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Your Privacy Choices', href: '/privacy-choices' },
  { label: 'Contact', href: '/contact' },
];

export default function LandingFooter() {
  return (
    <footer className="landing-footer" id="landing-footer">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8 py-8">
        {/* Links row */}
        <nav
          className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 mb-5"
          aria-label="Footer navigation"
        >
          {FOOTER_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-xs text-white/40 hover:text-[#76B900] transition-colors duration-200"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Copyright */}
        <p className="text-center text-[0.7rem] text-white/25 tracking-wide">
          Copyright © 2026 EXOPER
        </p>
      </div>
    </footer>
  );
}
