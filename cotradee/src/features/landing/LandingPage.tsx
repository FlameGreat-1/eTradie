import './landing.css';
import ParticlesCanvas from './components/ParticlesCanvas';
import LandingHeader from './components/LandingHeader';
import LandingHero from './components/LandingHero';
import ProcessFlow from './components/ProcessFlow';
import LandingFooter from './components/LandingFooter';

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
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}
