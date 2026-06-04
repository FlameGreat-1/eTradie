import React from 'react';

interface Props {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * A global Error Boundary designed exclusively to catch Vite dynamic import failures.
 * These occur when a user navigates to a lazy-loaded route after a new deployment
 * has invalidated the old chunk hashes on the server.
 * 
 * When caught, it silently forces a full page reload to fetch the new chunk manifests.
 * It uses a timestamp in sessionStorage to prevent infinite reload loops in case of 
 * genuine permanent server errors (e.g. broken builds).
 */
export class ChunkErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_error: Error): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, _errorInfo: React.ErrorInfo) {
    const message = error.message || '';
    const isChunkLoadError =
      error.name === 'ChunkLoadError' ||
      message.includes('Failed to fetch dynamically imported module') ||
      message.includes('Importing a module script failed');

    if (isChunkLoadError) {
      const lastRefreshStr = sessionStorage.getItem('vite-chunk-error-timestamp');
      const lastRefresh = lastRefreshStr ? parseInt(lastRefreshStr, 10) : 0;
      const now = Date.now();

      // Only attempt to auto-refresh if we haven't already done so in the last 10 seconds.
      if (now - lastRefresh > 10000) {
        sessionStorage.setItem('vite-chunk-error-timestamp', now.toString());
        window.location.reload();
        return;
      }
    }

    // If it's a different error, or we are caught in a rapid loop, re-throw to 
    // let standard error boundaries or the browser handle it.
    throw error;
  }

  render() {
    if (this.state.hasError) {
      // While the browser is reloading (or if we fell through and failed), 
      // render the fallback to avoid a blank flash or crashing the tree beneath.
      return <>{this.props.fallback}</>;
    }

    return <>{this.props.children}</>;
  }
}
