import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';
import { Toaster } from '@/components/ui/Toaster';

import UpgradeModal from '@/features/settings/components/UpgradeModal';
import QuotaExhaustedModal from '@/features/settings/components/QuotaExhaustedModal';
import ProviderQuotaModal from '@/features/settings/components/ProviderQuotaModal';
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
          Quota modals (Audit ref: ADMIN-QUOTA-13/14).

          Both are entirely event-driven: they listen for a window
          CustomEvent fired by RealtimeProvider (WS path) or by the
          axios interceptor (HTTP 429 path). When no event has fired
          they render null, so the runtime cost of mounting them is
          zero. They must mount at the App root (not inside any route)
          because a quota event can arrive on ANY page.

          QuotaExhaustedModal      - platform-key users (pro_managed +
                                     admin) whose platform quota cap
                                     was hit. Listens for
                                     'open-llm-quota-modal'.
          ProviderQuotaModal       - BYOK users whose OWN provider
                                     returned a quota / rate-limit
                                     error. Listens for
                                     'open-llm-provider-quota-modal'.
        */}
        <QuotaExhaustedModal />
        <ProviderQuotaModal />
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
