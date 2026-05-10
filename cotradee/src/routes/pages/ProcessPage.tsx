import '@/features/landing/landing.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';
import ProcessFlow from '@/features/landing/components/ProcessFlow';
import HowItWorks from '@/features/landing/components/HowItWorks';

/**
 * Public Process page — reachable at `/process`.
 *
 * Renders the same Process-related sections that appear on /landing,
 * in the same order, by composing the existing components without
 * modification:
 *
 *   1. <ProcessFlow />   — the pipeline diagram ("Process")
 *   2. <HowItWorks />    — the "How It Works" timeline + "Why It Works" grid
 *
 * The top padding (`pt-24`) compensates for the fixed LandingHeader
 * so the first content is not hidden behind the header on initial
 * load.
 */
export default function ProcessPage() {
  return (
    <div className="landing-page">
      <ParticlesCanvas />

      <div className="landing-content">
        <LandingHeader />

        <main className="pt-24">
          <ProcessFlow />
          <HowItWorks />
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}
