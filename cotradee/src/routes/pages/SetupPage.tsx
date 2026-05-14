import { OnboardingChecklist } from '@/features/tradingsystem/components/OnboardingChecklist';

/**
 * Standalone /dashboard/setup page.
 *
 * Renders the OnboardingChecklist as a centred card on a dedicated
 * route so a partially-onboarded user can resume the seven-step flow
 * without losing their chart context (the dashboard's Resume Setup
 * pill links here; the back button or sidebar returns the user to
 * the chart).
 *
 * The page is intentionally thin — the entire UI is owned by
 * OnboardingChecklist so a future tweak to the checklist is picked
 * up here automatically.
 */
export default function SetupPage() {
  return (
    <div className="flex h-full w-full overflow-y-auto bg-app">
      <OnboardingChecklist />
    </div>
  );
}
