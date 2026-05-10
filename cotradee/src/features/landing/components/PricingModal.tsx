import React, { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import ParticlesCanvas from './ParticlesCanvas';
import LandingHeader from './LandingHeader';

/**
 * Full-screen pricing/comparison overlay.
 *
 * Opened by dispatching the `open-pricing-modal` window event from
 * anywhere in the app (see LandingHeader's "Pricing" buttons).
 *
 * Design notes:
 *  - Uses the page's existing global scrollbar; we deliberately do NOT
 *    lock `document.body.overflow` and we do NOT add an inner
 *    `overflow-y-auto` so we don't get a second nested scrollbar.
 *  - Reuses the shared <LandingHeader> (same header as the home page)
 *    in its scrolled state, so navigation, theme toggle, countdown,
 *    and mobile menu all work identically.
 *  - There is no dedicated close button. Any header navigation
 *    (logo → "/", Process → "#process-flow", Sign In, Start Trading,
 *    or the Pricing toggle itself) triggers a route/hash change which
 *    is observed via `useLocation` and closes the modal.
 *  - The Esc key also closes the modal as a keyboard affordance.
 */
export default function PricingModal() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const previousScrollRef = useRef(0);

  // Open on global event
  useEffect(() => {
    const handleOpen = () => {
      previousScrollRef.current = window.scrollY;
      setIsOpen(true);
    };
    window.addEventListener('open-pricing-modal', handleOpen);
    return () => window.removeEventListener('open-pricing-modal', handleOpen);
  }, []);

  // While open: hide the underlying landing page by clipping the body so
  // the modal's own scroll container drives the page scrollbar. Restore
  // the previous scroll position on close so the user returns exactly
  // where they left off on the landing page.
  useEffect(() => {
    if (!isOpen) return;
    const previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousBodyOverflow;
      window.scrollTo({ top: previousScrollRef.current, behavior: 'auto' });
    };
  }, [isOpen]);

  // Close on Esc as a keyboard affordance (no visible close button).
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen]);

  // Auto-close whenever the route changes (e.g. "Get Started Now" → /register).
  // We skip the very first render so opening on the current route doesn't
  // immediately close the modal.
  const initialPathRef = useRef(location.pathname + location.search + location.hash);
  useEffect(() => {
    const current = location.pathname + location.search + location.hash;
    if (isOpen && current !== initialPathRef.current) {
      setIsOpen(false);
    }
    initialPathRef.current = current;
  }, [location, isOpen]);

  // Reset the modal's own scroll to the top whenever it (re)opens.
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (isOpen && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = 0;
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={scrollContainerRef}
      className="fixed inset-0 z-[120] overflow-y-auto bg-[#050505] animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Pricing comparison"
    >
      {/* Background particle system (purely decorative, ignores pointer events) */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[8%] left-[12%] w-[600px] h-[600px] bg-[#76b900] opacity-[0.08] blur-[120px] rounded-full" />
        <div className="absolute top-[32%] right-[22%] w-[400px] h-[400px] bg-[#76b900] opacity-[0.05] blur-[100px] rounded-full" />
        <div className="absolute bottom-[8%] left-[22%] w-[500px] h-[500px] bg-[#76b900] opacity-[0.04] blur-[120px] rounded-full" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\\\'0 0 256 256\\\' xmlns=\\\'http://www.w3.org/2000/svg\\\'%3E%3Cfilter id=\\\'n\\\'%3E%3CfeTurbulence type=\\\'fractalNoise\\\' baseFrequency=\\\'0.85\\\' numOctaves=\\\'4\\\' stitchTiles=\\\'stitch\\\'/%3E%3C/filter%3E%3Crect width=\\\'100%25\\\' height=\\\'100%25\\\' filter=\\\'url(%23n)\\\'/%3E%3C/svg%3E")' }}
        />
        <ParticlesCanvas />
      </div>

      <div className="relative z-10 w-full min-h-screen flex flex-col">

        {/* EXACT SAME HEADER FROM LANDING PAGE */}
        <LandingHeader forceScrolled={true} />

        {/* Main Content Area */}
        <div className="w-full max-w-[1000px] mx-auto px-6 pt-32 pb-32">
          <div className="text-center mb-16 mt-8">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white tracking-tight">
              Institutional-grade <span className="text-[#76b900]">intelligence</span>.
            </h2>
            <p className="text-white/40 text-lg max-w-2xl mx-auto">
              Choose the plan that fits your trading style. From casual analysis to institutional automation.
            </p>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent to-white/10" />
            <span className="text-xs font-bold text-white/20 uppercase tracking-[0.3em] whitespace-nowrap">Full Comparison</span>
            <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent to-white/10" />
          </div>

          {/* Comparison Table.
              Horizontal-only overflow on small viewports (table has a 600px
              minimum); the `hide-scrollbar` utility hides the horizontal
              scrollbar UI while keeping it scrollable. */}
          <div className="w-full overflow-x-auto pb-8 hide-scrollbar">
            <div className="min-w-[600px] bg-[#0a0a0a] border border-white/5 rounded-2xl shadow-2xl relative">
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#76B900]/30 to-transparent" />

              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-6 px-6 md:px-8 w-1/3 font-medium text-white/40 uppercase tracking-widest text-xs">Features</th>
                    <th className="py-6 px-6 md:px-8 w-1/3 text-center font-bold text-[#76B900] uppercase tracking-widest text-xs">Free</th>
                    <th className="py-6 px-6 md:px-8 w-1/3 text-center font-bold text-white/80 uppercase tracking-widest text-xs">Pro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  <Row title="Price" free="Free" pro="$49/mo" highlight />
                  <Row title="Account Required" free="Yes" pro="Yes" />
                  <Row title="Automated Execution" free="No" pro={<CheckIcon />} />
                  <Row title="Automated Scheduling" free="No" pro={<CheckIcon />} />
                  <Row title="AI Technical Analysis" free="1 per day" pro="Unlimited" />
                  <Row title="Custom Cycle Intervals" free="\u2014" pro={<CheckIcon />} />
                  <Row title="Live Chart Updates" free="Real-time" pro="Real-time" />
                  <Row title="Risk Engine Safeguards" free={<CheckIcon />} pro={<CheckIcon />} />
                  <Row title="Trade Journal" free="Basic" pro="Advanced" />
                  <Row title="Telegram Alerts" free="\u2014" pro={<CheckIcon />} />
                  <Row title="Support" free="Community" pro="Priority" />
                </tbody>
              </table>
            </div>
          </div>

          {/* Call to action at bottom.
              Defensive close on click — the route-change effect above will
              also close the modal once /register is reached, but doing it
              eagerly here removes any flash. */}
          <div className="mt-12 mb-16 flex justify-center text-center">
              <Link
                to="/register?returnTo=/dashboard/settings/billing"
                onClick={() => setIsOpen(false)}
                className="btn-cta-brand px-12 py-4 text-base"
              >
                Get Started Now
              </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ title, free, pro, highlight = false }: { title: string, free: React.ReactNode, pro: React.ReactNode, highlight?: boolean }) {
  return (
    <tr className={`hover:bg-white/[0.02] transition-colors ${highlight ? 'font-medium text-white' : 'text-white/70'}`}>
      <td className="py-5 px-6 md:px-8 whitespace-nowrap">{title}</td>
      <td className="py-5 px-6 md:px-8 text-center">{free}</td>
      <td className="py-5 px-6 md:px-8 text-center">{pro}</td>
    </tr>
  );
}

function CheckIcon() {
  return (
    <div className="flex justify-center">
      <div className="bg-[#76B900]/10 rounded-full p-1 border border-[#76B900]/20">
        <Check size={14} className="text-[#76B900]" />
      </div>
    </div>
  );
}
