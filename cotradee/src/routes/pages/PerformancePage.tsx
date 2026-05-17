import { PerformanceReviewView } from '@/features/performance';

/**
 * Performance Review dashboard page.
 *
 * Thin wrapper that mounts the feature module's top-level view
 * inside the dashboard layout chrome. All state, polling, and
 * rendering logic lives inside @/features/performance so the page
 * stays a pure routing target.
 *
 * The view itself is responsive (mobile / tablet / desktop) and
 * dark/light aware via tailwind's dark: prefix, matching the rest
 * of the dashboard surface.
 */
export default function PerformancePage() {
  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <PerformanceReviewView />
    </div>
  );
}
