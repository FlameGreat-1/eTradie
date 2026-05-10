import '@/features/landing/landing.css';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import LandingHeader from '@/features/landing/components/LandingHeader';
import LandingFooter from '@/features/landing/components/LandingFooter';
import ProcessFlow from '@/features/landing/components/ProcessFlow';

/**
 * Public Process page — reachable at `/process`.
 *
 * Renders the exact same <ProcessFlow /> component used as a section
 * on /landing, with no modifications, inside the same landing-page
 * chrome (background, particles, header, footer). This guarantees
 * the visual output and behavior match the /landing rendering of
 * Process byte-for-byte.
 *
 * The top padding (`pt-24`) compensates for the fixed LandingHeader
 * so the Process section's first content (its intro paragraph) is
 * not hidden behind the header on initial load.
 */
export default function ProcessPage() {
  return (
    <div className="landing-page">
      <ParticlesCanvas />

      <div className="landing-content">
        <LandingHeader />

        <main className="pt-24">
          <ProcessFlow />
        </main>

        <LandingFooter />
      </div>
    </div>
  );
}
