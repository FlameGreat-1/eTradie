import './landing.css';
import ParticlesCanvas from './components/ParticlesCanvas';
import LandingHeader from './components/LandingHeader';
import LandingHero from './components/LandingHero';
import ProcessFlow from './components/ProcessFlow';
import HowItWorks from './components/HowItWorks';
import CommunitySection from './components/CommunitySection';
import LandingFooter from './components/LandingFooter';

/**
 * Exoper public landing page.
 *
 * Rendered at "/" for unauthenticated visitors. Uses the NVIDIA-style
 * "Digital Nebula" background with green accents, stardust particles,
 * and a noise texture overlay.
 *
 * NOTE: <PricingModal /> is mounted globally in App.tsx so it can be
 * triggered from any route via the `open-pricing-modal` window event.
 * Do NOT mount a second instance here — doing so causes two stacked
 * overlays which break the "Get Started Now" CTA and double-toggle the
 * body scroll lock.
 */
export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* Background particle system */}
      <ParticlesCanvas />

      {/* Content layers (above background) */}
      <div className="landing-content">
        <LandingHeader />

        <main>
          <LandingHero />
          <ProcessFlow />
          <HowItWorks />
          {/*
            Public community entry points (Facebook / Discord /
            Telegram / WhatsApp). Reachable without an account and
            kept distinct from the staff-facing notification channels
            wired into the support backend. Section auto-hides when
            no SUPPORT_COMMUNITY_* env vars are configured.
          */}
          <CommunitySection />
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}
