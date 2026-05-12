import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';
import { Toaster } from '@/components/ui/Toaster';

import UpgradeModal from '@/features/settings/components/UpgradeModal';
import ConsentBanner from '@/features/consent/components/ConsentBanner';
import ConsentPreferencesModal from '@/features/consent/components/ConsentPreferencesModal';
import HelpAffordance from '@/components/help/HelpAffordance';

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <AppRoutes />
        <UpgradeModal />
        {/*
          Cookie-consent UI is mounted at the App root (not inside a
          route) so the banner and preferences modal can overlay every
          page, including the public marketing surface and the
          authenticated dashboard. The modal (z-index 100) sits above
          the banner (z-index 90) so opening Customise from the banner
          cleanly stacks them while the consent decision is being made.
        */}
        <ConsentBanner />
        <ConsentPreferencesModal />
        {/*
          Persistent help affordance. Renders a fixed bottom-right
          help button on every page where the chrome can accommodate
          it (see isHelpVisibleOnPath). For guests it navigates to
          /contact; for authenticated users it opens a popover with
          shortcuts into the Support Centre and the community
          channels. Hidden on /login, /register, /auth/*, and
          /contact (where the page itself IS the help surface).
        */}
        <HelpAffordance />
        <Toaster />
      </AppProvider>
    </ErrorBoundary>
  );
}
