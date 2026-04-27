import { AppProvider } from '@/providers/AppProvider';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import AppRoutes from '@/routes';

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </ErrorBoundary>
  );
}
