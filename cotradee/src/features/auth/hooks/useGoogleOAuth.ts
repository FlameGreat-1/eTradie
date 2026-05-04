import { useCallback, useRef, useState } from 'react';
import {
  startGoogleOAuth,
  completeGoogleOAuth,
  startGoogleLink,
  completeGoogleLink,
  unlinkGoogle,
} from '../api/oauth';
import {
  clearPendingOAuthFlow,
  pendingFlowMode,
  readPendingOAuthFlow,
  sanitiseReturnTo,
  savePendingOAuthFlow,
} from '../lib/oauthStorage';
import { useAuth } from '../context/AuthContext';
import type {
  OAuthCallbackResponse,
  OAuthLinkCallbackResponse,
} from '../types';

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

  /**
   * Begin a Google account-link for the currently authenticated user.
   * Marks the pending sessionStorage record with mode='link' so the
   * callback layer routes it to the link completion endpoint and
   * refuses to redeem it as a sign-in.
   */
  startGoogleLink: (returnTo?: string) => Promise<void>;

  /**
   * Finish a Google account-link. Verifies the pending record was
   * minted in link-mode, posts to the gateway's link callback,
   * refreshes AuthContext.user from the response, and clears the
   * pending record.
   */
  completeGoogleLink: (params: {
    code: string;
    state: string;
    error?: string | null;
  }) => Promise<OAuthLinkCallbackResponse>;

  /**
   * Remove the Google identity binding from the authenticated user
   * and refresh the profile so the UI updates immediately.
   */
  unlinkGoogle: () => Promise<void>;

  isStarting: boolean;
  isCompleting: boolean;
  isLinking: boolean;
  isCompletingLink: boolean;
  isUnlinking: boolean;
}

export function useGoogleOAuth(): UseGoogleOAuthResult {
  const { loginWithTokenPair, refreshUser } = useAuth();
  const [isStarting, setIsStarting] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [isLinking, setIsLinking] = useState(false);
  const [isCompletingLink, setIsCompletingLink] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);

  // Single-flight guards: prevent double-clicks on the start button or
  // the callback page double-mounting (e.g. React StrictMode in dev)
  // from racing the gateway with two callbacks for the same code.
  // Each flow keeps its own ref so the sign-in and link paths cannot
  // accidentally share busy state.
  const startInFlight = useRef(false);
  const completeInFlight = useRef(false);
  const linkInFlight = useRef(false);
  const completeLinkInFlight = useRef(false);
  const unlinkInFlight = useRef(false);

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
        mode: 'signin',
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

      // Tracks whether the local state check has passed for this
      // attempt. Once it has, the gateway-side flow row will be (or
      // has been) consumed atomically by the callback POST, so the
      // browser-side pending record must be cleared on ANY subsequent
      // failure path; otherwise a transient backend error would leave
      // a stale state in sessionStorage that causes the next attempt
      // to fail with "state did not match".
      let stateConsumed = false;

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
        // Refuse to redeem a link-mode pending record against the
        // sign-in callback. This is impossible to reach in normal use
        // (the routes are separate) but is cheap defence-in-depth.
        if (pendingFlowMode(pending) !== 'signin') {
          clearPendingOAuthFlow();
          throw new Error(
            'This sign-in link is for a different flow. Please start again from the login page.',
          );
        }
        if (pending.state !== state) {
          clearPendingOAuthFlow();
          throw new Error(
            'Sign-in state did not match. Please start again from the login page.',
          );
        }
        stateConsumed = true;

        const res = await completeGoogleOAuth({ code, state });
        if (!res?.tokens?.access_token || !res?.tokens?.refresh_token) {
          throw new Error('Gateway did not return a usable token pair.');
        }

        // Hydrate AuthContext exactly like a username/password login.
        await loginWithTokenPair(res.tokens, res.user);
        clearPendingOAuthFlow();
        return res;
      } catch (err) {
        if (stateConsumed) {
          // The server-side flow row has been consumed (or is about to
          // be); the locally-cached state is now useless. Clear it so
          // the user can immediately retry from /login without hitting
          // a phantom "state did not match".
          clearPendingOAuthFlow();
        }
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

  const startLink = useCallback(async (returnTo?: string) => {
    if (linkInFlight.current) return;
    linkInFlight.current = true;
    setIsLinking(true);
    try {
      const safeReturnTo = sanitiseReturnTo(returnTo);
      const res = await startGoogleLink({ return_to: safeReturnTo });
      if (!res?.authorize_url || !res?.state) {
        throw new Error('gateway returned an invalid authorize response');
      }
      savePendingOAuthFlow({
        state: res.state,
        returnTo: safeReturnTo,
        startedAt: Date.now(),
        mode: 'link',
      });
      window.location.assign(res.authorize_url);
    } catch (err) {
      linkInFlight.current = false;
      setIsLinking(false);
      throw new Error(
        normaliseError(err, 'Could not start Google account link'),
      );
    }
  }, []);

  const completeLink = useCallback(
    async ({
      code,
      state,
      error,
    }: {
      code: string;
      state: string;
      error?: string | null;
    }): Promise<OAuthLinkCallbackResponse> => {
      if (completeLinkInFlight.current) {
        throw new Error('Google account link is already in progress');
      }
      completeLinkInFlight.current = true;
      setIsCompletingLink(true);

      let stateConsumed = false;

      try {
        if (error && error.trim() !== '') {
          throw new Error(
            error === 'access_denied'
              ? 'Google account link was cancelled.'
              : `Google returned an error: ${error}`,
          );
        }
        if (!code || !state) {
          throw new Error('Missing code or state from Google.');
        }
        const pending = readPendingOAuthFlow();
        if (!pending) {
          throw new Error(
            'This link request is no longer valid. Please start again from settings.',
          );
        }
        // Refuse to redeem a sign-in pending record against the link
        // callback; the modes are not interchangeable.
        if (pendingFlowMode(pending) !== 'link') {
          clearPendingOAuthFlow();
          throw new Error(
            'This link request is for a different flow. Please start again from settings.',
          );
        }
        if (pending.state !== state) {
          clearPendingOAuthFlow();
          throw new Error(
            'Link state did not match. Please start again from settings.',
          );
        }
        stateConsumed = true;

        const res = await completeGoogleLink({ code, state });
        // Refresh the profile so auth_provider / email_verified update
        // in the UI without a manual reload. The gateway also returns
        // res.user, but refreshUser keeps a single source of truth.
        await refreshUser();
        clearPendingOAuthFlow();
        return res;
      } catch (err) {
        if (stateConsumed) {
          clearPendingOAuthFlow();
        }
        throw new Error(
          normaliseError(err, 'Could not finish Google account link'),
        );
      } finally {
        completeLinkInFlight.current = false;
        setIsCompletingLink(false);
      }
    },
    [refreshUser],
  );

  const unlink = useCallback(async () => {
    if (unlinkInFlight.current) return;
    unlinkInFlight.current = true;
    setIsUnlinking(true);
    try {
      await unlinkGoogle();
      await refreshUser();
    } catch (err) {
      throw new Error(
        normaliseError(err, 'Could not unlink Google account'),
      );
    } finally {
      unlinkInFlight.current = false;
      setIsUnlinking(false);
    }
  }, [refreshUser]);

  return {
    startGoogleOAuth: start,
    completeGoogleOAuth: complete,
    startGoogleLink: startLink,
    completeGoogleLink: completeLink,
    unlinkGoogle: unlink,
    isStarting,
    isCompleting,
    isLinking,
    isCompletingLink,
    isUnlinking,
  };
}
