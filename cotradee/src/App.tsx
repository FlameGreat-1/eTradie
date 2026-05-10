import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';
import { Toaster } from '@/components/ui/Toaster';

import UpgradeModal from '@/features/settings/components/UpgradeModal';

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <AppRoutes />
        <UpgradeModal />
        <Toaster />
      </AppProvider>
    </ErrorBoundary>
  );
}
