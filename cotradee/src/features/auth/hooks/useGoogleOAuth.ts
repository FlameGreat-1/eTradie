import { useCallback, useRef, useState } from 'react';
import { startGoogleOAuth, completeGoogleOAuth } from '../api/oauth';
import {
  clearPendingOAuthFlow,
  readPendingOAuthFlow,
  sanitiseReturnTo,
  savePendingOAuthFlow,
} from '../lib/oauthStorage';
import { useAuth } from '../context/AuthContext';
import type { OAuthCallbackResponse } from '../types';

/**
 * Map an axios / network error into a short user-facing string.
 * Avoids leaking internal stack traces while preserving the gateway's
 * `error` field when present.
 */
function normaliseError(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const maybe = err as {
      response?: { data?: { error?: string } };
      message?: string;
    };
    const fromBody = maybe.response?.data?.error;
    if (typeof fromBody === 'string' && fromBody.trim() !== '') {
      return fromBody;
    }
    if (typeof maybe.message === 'string' && maybe.message.trim() !== '') {
      return maybe.message;
    }
  }
  return fallback;
}

export interface UseGoogleOAuthResult {
  /**
   * Begin a Google sign-in. Calls the gateway, persists the returned
   * state in sessionStorage, and navigates the browser to Google's
   * consent page. Resolves only on failure (success leaves the page).
   */
  startGoogleOAuth: (returnTo?: string) => Promise<void>;

  /**
   * Finish a Google sign-in. Validates the state echoed by Google
   * against the value the gateway handed us at start-time, posts the
   * code+state to the gateway, hydrates the AuthContext via the
   * existing token pipeline, and returns the gateway's response
   * (including the resolved return_to path).
   */
  completeGoogleOAuth: (params: {
    code: string;
    state: string;
    error?: string | null;
  }) => Promise<OAuthCallbackResponse>;

  isStarting: boolean;
  isCompleting: boolean;
}

export function useGoogleOAuth(): UseGoogleOAuthResult {
  const { loginWithTokenPair } = useAuth();
  const [isStarting, setIsStarting] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);

  // Single-flight guard: prevent double-clicks on the start button or
  // the callback page double-mounting (e.g. React StrictMode in dev)
  // from racing the gateway with two callbacks for the same code.
  const startInFlight = useRef(false);
  const completeInFlight = useRef(false);

  const start = useCallback(async (returnTo?: string) => {
    if (startInFlight.current) return;
    startInFlight.current = true;
    setIsStarting(true);
    try {
      const safeReturnTo = sanitiseReturnTo(returnTo);
      const res = await startGoogleOAuth({ return_to: safeReturnTo });
      if (!res?.authorize_url || !res?.state) {
        throw new Error('gateway returned an invalid authorize response');
      }
      savePendingOAuthFlow({
        state: res.state,
        returnTo: safeReturnTo,
        startedAt: Date.now(),
      });
      // Hand the browser off to Google. window.location.assign keeps a
      // history entry so the back button returns to /login.
      window.location.assign(res.authorize_url);
    } catch (err) {
      startInFlight.current = false;
      setIsStarting(false);
      throw new Error(normaliseError(err, 'Could not start Google sign-in'));
    }
  }, []);

  const complete = useCallback(
    async ({
      code,
      state,
      error,
    }: {
      code: string;
      state: string;
      error?: string | null;
    }): Promise<OAuthCallbackResponse> => {
      if (completeInFlight.current) {
        throw new Error('Google sign-in is already in progress');
      }
      completeInFlight.current = true;
      setIsCompleting(true);
      try {
        if (error && error.trim() !== '') {
          throw new Error(
            error === 'access_denied'
              ? 'Google sign-in was cancelled.'
              : `Google returned an error: ${error}`,
          );
        }
        if (!code || !state) {
          throw new Error('Missing code or state from Google.');
        }
        const pending = readPendingOAuthFlow();
        if (!pending) {
          throw new Error(
            'This sign-in link is no longer valid. Please start again from the login page.',
          );
        }
        if (pending.state !== state) {
          clearPendingOAuthFlow();
          throw new Error(
            'Sign-in state did not match. Please start again from the login page.',
          );
        }

        const res = await completeGoogleOAuth({ code, state });
        if (!res?.tokens?.access_token || !res?.tokens?.refresh_token) {
          throw new Error('Gateway did not return a usable token pair.');
        }

        // Hydrate AuthContext exactly like a username/password login.
        await loginWithTokenPair(res.tokens, res.user);
        clearPendingOAuthFlow();
        return res;
      } catch (err) {
        throw new Error(
          normaliseError(err, 'Could not finish Google sign-in'),
        );
      } finally {
        completeInFlight.current = false;
        setIsCompleting(false);
      }
    },
    [loginWithTokenPair],
  );

  return {
    startGoogleOAuth: start,
    completeGoogleOAuth: complete,
    isStarting,
    isCompleting,
  };
}
