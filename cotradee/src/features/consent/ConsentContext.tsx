/**
 * ConsentProvider owns the live cookie-consent state for the SPA.
 *
 * Order of operations on first paint:
 *
 *  1. Read local storage (instant). If a recorded decision is found
 *     for the current policy version, set state to it and clear
 *     needsDecision. The banner stays hidden. `hydrated` flips to
 *     true at this point so any UI gated on it renders without
 *     waiting for the server.
 *
 *  2. Fire GET /api/v1/consent in parallel. If the server returns a
 *     newer record (newer policy_version OR newer timestamp) we
 *     mirror it into local storage and adopt it. This handles the
 *     'recorded on another device' case.
 *
 *  3. If no decision is found anywhere AND the policy version has
 *     bumped since the recorded one, needsDecision becomes true and
 *     the banner renders.
 *
 * Writes flow through acceptAll / rejectAll / saveCustom; each:
 *  - persists locally first (so the UI updates instantly),
 *  - then POSTs to the server,
 *  - on POST failure: rolls back local storage and surfaces a toast,
 *  - on success: flips `decisionMadeThisSession` so the auth bridge
 *    knows the current anonymous_id is safe to attach to a new user.
 */

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { toast } from '@/hooks/useToast';
import {
  type ConsentDecision,
  type ConsentState,
  CONSENT_POLICY_VERSION,
  acceptAllDecision,
  rejectAllDecision,
} from './types';
import {
  attachAnonymousToUser,
  fetchLatestConsent,
  postConsent,
} from './api';
import {
  getOrCreateAnonymousId,
  mirrorServerRecord,
  readDecisionMadeThisSession,
  readStoredDecision,
  writeDecisionMadeThisSession,
  writeStoredDecision,
} from './storage';

export const ConsentContext = createContext<ConsentState | undefined>(undefined);

export function ConsentProvider({ children }: { children: ReactNode }) {
  // Anonymous id is generated synchronously so the first render
  // already has a stable id available for the banner's eventual POST.
  const anonymousIdRef = useRef<string>(getOrCreateAnonymousId());
  const anonymousId = anonymousIdRef.current;

  const [hydrated, setHydrated] = useState(false);
  const [needsDecision, setNeedsDecision] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  // Defensive default: every optional category off until the user
  // actively opts in. Strictly-necessary cookies are not part of
  // ConsentDecision and remain on regardless.
  const [decision, setDecision] = useState<ConsentDecision>(() => rejectAllDecision());
  const [recordedPolicyVersion, setRecordedPolicyVersion] = useState<string>('');
  // Flipped true the moment the user actively makes a decision in
  // this tab. Stays false when the only decision available was
  // loaded from pre-existing local storage. Used by the auth bridge
  // to decide whether attaching the anonymous_id to a freshly-
  // authenticated user is safe (a shared-computer scenario otherwise
  // attaches a stranger's prior decision to the new user's account).
  //
  // Seeded from sessionStorage so a refresh of THIS tab between the
  // decision and the sign-up does not lose the safe-to-attach
  // signal. sessionStorage is tab-scoped and tab-lifetime, so a
  // stranger reopening the browser starts at false again.
  const [decisionMadeThisSession, setDecisionMadeThisSessionState] = useState<boolean>(
    () => readDecisionMadeThisSession(),
  );

  // Write-through wrapper so React state and sessionStorage never
  // drift. Every persist / rollback path uses this single setter.
  const setDecisionMadeThisSession = useCallback((made: boolean) => {
    setDecisionMadeThisSessionState(made);
    writeDecisionMadeThisSession(made);
  }, []);

  // ----- Initial hydrate -----
  useEffect(() => {
    let cancelled = false;

    // 1. Local storage first — instant and offline-friendly.
    const local = readStoredDecision();
    if (local) {
      setDecision(local.decision);
      setRecordedPolicyVersion(local.policyVersion);
      setNeedsDecision(local.policyVersion !== CONSENT_POLICY_VERSION);
    } else {
      // No local record — must prompt unless the server has one.
      setNeedsDecision(true);
    }
    // Flip hydrated as soon as the synchronous read is done. The
    // server reconcile below continues in the background and may
    // overwrite local state if it returns a newer record. This
    // prevents the banner from being suppressed for up to 5 minutes
    // (the axios default timeout) on a flaky network.
    setHydrated(true);

    // 2. Server reconcile. Use the anonymous id when the user is
    // not authenticated; when authenticated the gateway derives the
    // user_id from the access cookie automatically.
    void fetchLatestConsent(anonymousId).then((rec) => {
      if (cancelled) return;
      if (!rec) return;
      const localTs = local ? local.recordedAt : 0;
      const serverTs = Date.parse(rec.created_at) || 0;
      if (serverTs >= localTs) {
        mirrorServerRecord(rec);
        setDecision(rec.categories);
        setRecordedPolicyVersion(rec.policy_version);
        setNeedsDecision(rec.policy_version !== CONSENT_POLICY_VERSION);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [anonymousId]);

  // ----- Persist helper used by every write path -----
  const persist = useCallback(
    async (next: ConsentDecision): Promise<void> => {
      const previous = decision;
      const previousVersion = recordedPolicyVersion;
      const previousSessionFlag = decisionMadeThisSession;

      // Optimistic local write.
      const stored = writeStoredDecision(next);
      setDecision(stored.decision);
      setRecordedPolicyVersion(stored.policyVersion);
      setNeedsDecision(false);
      // The user just actively chose; the bridge may now safely
      // attach this anonymous_id on a subsequent login. This also
      // writes through to sessionStorage so a tab refresh before
      // sign-up preserves the safe-to-attach signal.
      setDecisionMadeThisSession(true);

      try {
        await postConsent({
          anonymousId,
          policyVersion: CONSENT_POLICY_VERSION,
          decision: next,
        });
      } catch (err) {
        // Roll back so the banner reappears and the user can retry.
        setDecision(previous);
        setRecordedPolicyVersion(previousVersion);
        // Roll back the session flag too: the user did not actually
        // succeed in recording a decision this tab.
        setDecisionMadeThisSession(previousSessionFlag);
        setNeedsDecision(true);
        toast({
          title: 'Could not save preference',
          description: 'Your cookie preference will be re-prompted shortly.',
          variant: 'warning',
        });
        throw err;
      }
    },
    [
      anonymousId,
      decision,
      recordedPolicyVersion,
      decisionMadeThisSession,
      setDecisionMadeThisSession,
    ],
  );

  const acceptAll = useCallback(() => persist(acceptAllDecision()), [persist]);
  const rejectAll = useCallback(() => persist(rejectAllDecision()), [persist]);
  const saveCustom = useCallback((d: ConsentDecision) => persist(d), [persist]);

  const openPreferences = useCallback(() => setPreferencesOpen(true), []);
  const closePreferences = useCallback(() => setPreferencesOpen(false), []);

  const attachToCurrentUser = useCallback(async () => {
    await attachAnonymousToUser(anonymousId);
  }, [anonymousId]);

  const value = useMemo<ConsentState>(
    () => ({
      hydrated,
      needsDecision,
      preferencesOpen,
      decision,
      anonymousId,
      recordedPolicyVersion,
      decisionMadeThisSession,
      acceptAll,
      rejectAll,
      saveCustom,
      openPreferences,
      closePreferences,
      attachToCurrentUser,
    }),
    [
      hydrated,
      needsDecision,
      preferencesOpen,
      decision,
      anonymousId,
      recordedPolicyVersion,
      decisionMadeThisSession,
      acceptAll,
      rejectAll,
      saveCustom,
      openPreferences,
      closePreferences,
      attachToCurrentUser,
    ],
  );

  return <ConsentContext.Provider value={value}>{children}</ConsentContext.Provider>;
}
