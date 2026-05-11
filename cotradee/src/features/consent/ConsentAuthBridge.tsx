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
 * IMPORTANT (PRACTICE.md #5): the bridge only fires when the user
 * actively made a consent decision in the CURRENT tab session
 * (consent.decisionMadeThisSession === true). Without this guard a
 * shared-computer scenario would silently attach a stranger's prior
 * decision (loaded from local storage left by the previous occupant)
 * to the freshly-authenticated user. That corrupts the GDPR Art. 7.1
 * audit-trail integrity. Users who log in without making a decision
 * in this tab will have nothing attached; their next decision (the
 * one they actually make) will be inserted with their user_id
 * already populated via OptionalAuth.
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

    // Audit-trail integrity guard. Without this, a fresh sign-in on
    // a shared computer would attach a stranger's earlier decision
    // to the new user_id.
    if (!consent.decisionMadeThisSession) return;

    attached.current = true;
    void consent.attachToCurrentUser();
  }, [
    isAuthenticated,
    isLoading,
    consent.hydrated,
    consent.decisionMadeThisSession,
    consent,
  ]);

  return null;
}
