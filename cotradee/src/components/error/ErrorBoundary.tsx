import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // Surface in dev so the issue is visible without a remote sink.
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('[ErrorBoundary]', error, info?.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    if (typeof window !== 'undefined') window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(
          this.state.error ?? new Error('Unknown error'),
          this.handleReset,
        );
      }
      return (
        <div className="flex flex-col items-center justify-center h-full gap-4 p-8 bg-app">
          <AlertTriangle size={40} className="text-danger" />
          <h2 className="text-lg font-bold text-content">Something went wrong</h2>
          <p className="text-sm text-content-muted max-w-md text-center">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-sm font-semibold
                         text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
            >
              <RefreshCw size={14} />
              Try Again
            </button>
            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm font-medium
                         text-content hover:bg-surface-3 transition-colors duration-fast focus-ring"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
