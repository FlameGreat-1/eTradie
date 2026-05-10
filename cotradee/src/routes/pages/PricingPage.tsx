import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import '@/features/landing/landing.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';

/**
 * Public pricing page — reachable at `/pricing`.
 *
 * This is a regular in-flow page, not an overlay. It reuses the
 * landing-page chrome (`.landing-page` background, ParticlesCanvas,
 * shared LandingHeader and LandingFooter) so it sits inside the same
 * visual world as `/landing`, and it scrolls with the document's own
 * scrollbar — no fixed wrappers, no body scroll lock, no nested
 * scroll containers.
 */
export default function PricingPage() {
  return (
    <div className="landing-page">
      {/* Background particle system (same one used on /landing) */}
      <ParticlesCanvas />

      <div className="landing-content">
        <LandingHeader />

        <main className="w-full max-w-[1000px] mx-auto px-6 pt-32 pb-32">
          <div className="text-center mb-16 mt-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight" style={{ color: 'var(--landing-text)' }}>
              Institutional-grade <span className="text-[#76b900]">intelligence</span>.
            </h1>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'var(--landing-text-faint)' }}>
              Choose the plan that fits your trading style. From casual analysis to institutional automation.
            </p>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent" style={{ backgroundImage: 'linear-gradient(to right, transparent, var(--landing-card-border))' }} />
            <span
              className="text-xs font-bold uppercase tracking-[0.3em] whitespace-nowrap"
              style={{ color: 'var(--landing-text-faint)' }}
            >
              Full Comparison
            </span>
            <div className="h-[1px] flex-1" style={{ backgroundImage: 'linear-gradient(to left, transparent, var(--landing-card-border))' }} />
          </div>

          {/* Comparison Table.
              Horizontal-only overflow on small viewports (table has a
              600px minimum). The `hide-scrollbar` utility hides the
              horizontal scrollbar UI while keeping it scrollable. */}
          <div className="w-full overflow-x-auto pb-8 hide-scrollbar">
            <div
              className="min-w-[600px] rounded-2xl shadow-2xl relative"
              style={{
                background: 'var(--landing-card-bg)',
                border: '1px solid var(--landing-card-border)',
              }}
            >
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#76B900]/30 to-transparent" />

              <table className="w-full text-sm text-left">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--landing-card-border)' }}>
                    <th
                      className="py-6 px-6 md:px-8 w-1/3 font-medium uppercase tracking-widest text-xs"
                      style={{ color: 'var(--landing-text-faint)' }}
                    >
                      Features
                    </th>
                    <th className="py-6 px-6 md:px-8 w-1/3 text-center font-bold text-[#76B900] uppercase tracking-widest text-xs">
                      Free
                    </th>
                    <th
                      className="py-6 px-6 md:px-8 w-1/3 text-center font-bold uppercase tracking-widest text-xs"
                      style={{ color: 'var(--landing-text)' }}
                    >
                      Pro
                    </th>
                  </tr>
                </thead>
                <tbody>
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
                  <Row title="Support" free="Community" pro="Priority" last />
                </tbody>
              </table>
            </div>
          </div>

          {/* Call to action */}
          <div className="mt-12 mb-16 flex justify-center text-center">
            <Link
              to="/register?returnTo=/dashboard/settings/billing"
              className="btn-cta-brand px-12 py-4 text-base"
            >
              Get Started Now
            </Link>
          </div>
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}

function Row({
  title,
  free,
  pro,
  highlight = false,
  last = false,
}: {
  title: string;
  free: React.ReactNode;
  pro: React.ReactNode;
  highlight?: boolean;
  last?: boolean;
}) {
  return (
    <tr
      className="transition-colors"
      style={{
        borderBottom: last ? 'none' : '1px solid var(--landing-card-border)',
        color: highlight ? 'var(--landing-text)' : 'var(--landing-text-muted)',
        fontWeight: highlight ? 500 : 400,
      }}
    >
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
