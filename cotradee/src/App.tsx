import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';
import { Toaster } from '@/components/ui/Toaster';

import PricingModal from '@/features/landing/components/PricingModal';
import UpgradeModal from '@/features/settings/components/UpgradeModal';

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <AppRoutes />
        <PricingModal />
        <UpgradeModal />
        <Toaster />
      </AppProvider>
    </ErrorBoundary>
  );
}
