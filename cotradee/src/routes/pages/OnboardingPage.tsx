import { OnboardingWizard } from '@/features/onboarding/components/OnboardingWizard';

/**
 * /onboarding route page.
 * Centered full-screen layout.
 */
export default function OnboardingPage() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-black p-6">
      <OnboardingWizard />
    </div>
  );
}
