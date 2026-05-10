import './landing.css';
import ParticlesCanvas from './components/ParticlesCanvas';
import LandingHeader from './components/LandingHeader';
import LandingHero from './components/LandingHero';
import ProcessFlow from './components/ProcessFlow';
import HowItWorks from './components/HowItWorks';
import LandingFooter from './components/LandingFooter';
import PricingModal from './components/PricingModal';

/**
 * Exoper public landing page.
 *
 * Rendered at "/" for unauthenticated visitors. Uses the NVIDIA-style
 * "Digital Nebula" background with green accents, stardust particles,
 * and a noise texture overlay.
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
        </main>

        <LandingFooter />
        <PricingModal />
      </div>
    </div>
  );
}
