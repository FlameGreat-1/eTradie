/**
 * ConsentAuthBridge keeps AuthContext and ConsentContext mutually
 * ignorant of each other while still doing the one thing they need
 * to coordinate on: anonymous-to-user attach.
 *
 * On the false -> true transition of useAuth().isAuthenticated, the
 * bridge fires POST /api/v1/consent/attach exactly once per session
 * so every consent_records row carrying the visitor's anonymous_id
 * picks up the now-known user_id without losing the original
 * recorded_at timestamp.
 *
 * The bridge renders nothing; it is mounted under ConsentProvider in
 * the AppProvider stack purely for its useEffect side-effect.
 */

import { useEffect, useRef } from 'react';
import { useAuth } from '@/features/auth';
import { useConsent } from './useConsent';

export default function ConsentAuthBridge() {
  const { isAuthenticated, isLoading } = useAuth();
  const consent = useConsent();
  const attached = useRef(false);

  useEffect(() => {
    // Wait for the AuthProvider's first /auth/me reconcile to settle
    // so we never attach against an undefined initial state.
    if (isLoading) return;
    if (!isAuthenticated) {
      // Logged out (either never logged in, or just logged out): reset
      // the latch so a future login can attach again.
      attached.current = false;
      return;
    }
    if (attached.current) return;

    // Wait for ConsentProvider to finish hydrating too so attach is
    // never sent with an anonymous_id that the context has not yet
    // confirmed against local storage / server.
    if (!consent.hydrated) return;

    attached.current = true;
    void consent.attachToCurrentUser();
  }, [isAuthenticated, isLoading, consent.hydrated, consent]);

  return null;
}
