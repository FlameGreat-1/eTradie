import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';
import { Toaster } from '@/components/ui/Toaster';

import UpgradeModal from '@/features/settings/components/UpgradeModal';
import ConsentBanner from '@/features/consent/components/ConsentBanner';
import ConsentPreferencesModal from '@/features/consent/components/ConsentPreferencesModal';

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
        <Toaster />
      </AppProvider>
    </ErrorBoundary>
  );
}
