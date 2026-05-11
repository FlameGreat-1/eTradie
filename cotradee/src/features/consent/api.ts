/**
 * Typed wrappers around the gateway's /api/v1/consent endpoints.
 *
 * Network failures are surfaced as null returns (for reads) or thrown
 * errors (for writes) so callers can decide how to react. The context
 * treats a read failure as 'no server record' and falls back to local
 * storage; a write failure is shown to the user via the existing
 * toast system.
 *
 * No backend types are duplicated here; the on-the-wire shapes are
 * imported from `./types` so a server schema change is a TypeScript
 * compile error against the same source of truth used by the UI.
 */

import { api } from '@/lib/axios';
import type { ConsentDecision, ConsentRecord } from './types';

interface ConsentEnvelope {
  record: ConsentRecord | null;
}

/**
 * Fetch the most-recent consent record for the visitor.
 *
 * - Authenticated callers pass `anonymousId` as `null`; the server uses
 *   the cookie-authenticated user_id to resolve the latest decision.
 * - Anonymous callers MUST pass anonymousId; the server uses it as the
 *   lookup key.
 *
 * Returns null when no record exists or when the request fails (the
 * caller cannot meaningfully distinguish the two for UX purposes and
 * both lead to the same fallback path: rely on local storage).
 */
export async function fetchLatestConsent(anonymousId: string | null): Promise<ConsentRecord | null> {
  try {
    const params = anonymousId ? { anonymous_id: anonymousId } : undefined;
    const { data } = await api.gateway.get<ConsentEnvelope>('/api/v1/consent', { params });
    return data.record ?? null;
  } catch {
    return null;
  }
}

/**
 * Record a fresh consent decision. The server appends a new immutable
 * row and returns it. Throws on transport / server failure so the
 * context can surface a toast and let the user retry.
 */
export async function postConsent(params: {
  anonymousId: string;
  policyVersion: string;
  decision: ConsentDecision;
}): Promise<ConsentRecord> {
  const { data } = await api.gateway.post<ConsentEnvelope>('/api/v1/consent', {
    anonymous_id: params.anonymousId,
    policy_version: params.policyVersion,
    categories: params.decision,
  });
  if (!data.record) {
    throw new Error('consent service returned empty record');
  }
  return data.record;
}

/**
 * Link every pre-login consent row carrying the given anonymous_id to
 * the now-authenticated user. Idempotent on the server (SQL UPDATE
 * with WHERE user_id IS NULL).
 *
 * Returns the number of rows attached, or null on failure (the caller
 * treats both 0 and null as 'no-op').
 */
export async function attachAnonymousToUser(anonymousId: string): Promise<number | null> {
  try {
    const { data } = await api.gateway.post<{ attached: number }>('/api/v1/consent/attach', {
      anonymous_id: anonymousId,
    });
    return typeof data.attached === 'number' ? data.attached : 0;
  } catch {
    return null;
  }
}

/**
 * Fetch the authenticated user's full consent history (newest-first),
 * up to `limit` rows (server-enforced cap of 100). Backs the GDPR
 * Article 15 right-of-access response surfaced by the Settings page.
 */
export async function fetchConsentHistory(limit = 25): Promise<ConsentRecord[]> {
  const { data } = await api.gateway.get<{ records: ConsentRecord[] }>(
    '/api/v1/consent/history',
    { params: { limit } },
  );
  return Array.isArray(data.records) ? data.records : [];
}
