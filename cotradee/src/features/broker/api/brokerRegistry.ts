import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

// ---------------------------------------------------------------------------
// Types — mirror the Pydantic models in src/engine/ta/broker/registry.py
// (BrokerBrand / BrokerEntity / PlatformConfig / EntityServers) so the
// frontend and the engine's GET /api/broker/registry response cannot
// drift. Every field name uses the engine's snake_case verbatim — the
// engine returns `.model_dump()` and Pydantic preserves the field names
// from the Python class.
//
// Reference: MT5_Multi_Broker_Provisioning_Architecture.md §5.2.
// ---------------------------------------------------------------------------

export type PlatformId = 'mt4' | 'mt5';
export type InstallerPackaging = 'unified' | 'per_entity' | 'none' | 'unknown';
export type BrandStatus = 'active' | 'pending_bake' | 'unsupported_mt5' | 'inactive';

export interface ServerLists {
  /** Demo / paper-trading servers. May be empty for live-only brokers. */
  demo: string[];
  /** Live trading servers. Active brands have at least one entry. */
  live: string[];
}

export interface PlatformConfig {
  /** Human-only acquisition URL (operator bake). NEVER fetched at runtime. */
  acquisition_url?: string | null;
  /** System fetch path the engine's initContainer wget-fetches. */
  bundle_r2_path: string;
  /** SHA256 of the baked portable zip. 64 lowercase hex chars. */
  bundle_sha256: string;
  /** ISO date the §3.5 verification gate last passed. Advisory. */
  verified_on?: string | null;
  /** Exact server strings extracted verbatim from the broker's servers.dat. */
  servers: ServerLists;
}

export interface EntityRecord {
  /** brand-prefixed lowercase underscore-separated id, e.g. 'exness_technologies_ltd'. */
  entity_id: string;
  /** Legal entity name as the broker publishes it. */
  display_name: string;
  /** Short regulator label, e.g. 'FSA Seychelles'. Advisory only. */
  regulator?: string | null;
  /** Platform-specific provisioning data. Single-platform brokers carry one key. */
  platforms: Partial<Record<PlatformId, PlatformConfig>>;
}

export interface BrandRecord {
  /** lowercase underscore-separated id, e.g. 'deriv', 'exness'. */
  brand_id: string;
  /** Brand name exactly as the broker presents it. */
  display_name: string;
  /** Broker's own official website (https). */
  official_website: string;
  /** Whether the broker offers an MT5 terminal at all. */
  mt5_supported: boolean;
  /** Whether the broker offers an MT4 terminal at all. */
  mt4_supported: boolean;
  /** Packaging convention for the broker's installer. */
  installer_packaging: InstallerPackaging;
  /** Lifecycle state. Only 'active' brands are resolvable for provisioning. */
  status: BrandStatus;
  /** Free-text operator notes. */
  notes?: string | null;
  /** Legal entities under this brand. Single-entity brands carry one record. */
  entities: EntityRecord[];
}

export interface BrokerRegistryResponse {
  brands: BrandRecord[];
}

// ---------------------------------------------------------------------------
// React Query hook
// ---------------------------------------------------------------------------

/**
 * Returns the active-brands catalogue the engine exposes at
 * GET /api/broker/registry. The catalog only mutates on a backend
 * deploy (a new brand JSON file lands under
 * infrastructure/broker-catalog/*.json and the engine re-loads on
 * boot), so the cache is long-lived. enabled is gated on auth so
 * the public landing pages do not poll the engine.
 */
export function useBrokerRegistry() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker', 'registry'],
    queryFn: async (): Promise<BrandRecord[]> => {
      const { data } = await api.engine.get<BrokerRegistryResponse>('/api/broker/registry');
      return data?.brands ?? [];
    },
    enabled: isAuthenticated,
    // The catalog is operator-owned config-as-code; once loaded it does
    // not change until the engine rolls. Keep the data fresh for 5
    // minutes and never auto-refetch on focus / reconnect.
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

// ---------------------------------------------------------------------------
// Derived helpers — used by FindBrokerStep + BrokerStep so the
// brand→entity→platform→server walk is consistent across both surfaces.
// ---------------------------------------------------------------------------

/**
 * Locate an entity inside a brand by its entity_id. Returns null when
 * the id is unknown (e.g. a row that pre-dates a catalog change).
 * Single-entity brands (Deriv, v1 Exness) are typically resolved by
 * the caller via `brand.entities[0]`; this helper is for multi-entity
 * brands where the user picks one.
 */
export function findEntity(brand: BrandRecord, entityId: string): EntityRecord | null {
  return brand.entities.find((e) => e.entity_id === entityId) ?? null;
}

/**
 * Return the demo + live server lists for an entity + platform pair.
 * Falls back to empty arrays when the platform is not configured for
 * that entity (e.g. an entity that only supports MT5). Callers can
 * render a 'no servers configured' state without a null check.
 */
export function resolveServers(
  entity: EntityRecord | null | undefined,
  platform: PlatformId,
): ServerLists {
  const pf = entity?.platforms?.[platform];
  if (!pf) return { demo: [], live: [] };
  return {
    demo: pf.servers?.demo ?? [],
    live: pf.servers?.live ?? [],
  };
}

/**
 * Flatten an entity's MT5 + MT4 server lists into a single sorted
 * list suitable for the wizard dropdown when the caller has not yet
 * narrowed the platform. The MT5 entries come first (the platform's
 * default) followed by MT4. Duplicates are de-duplicated.
 */
export function resolveAllServersForEntity(entity: EntityRecord | null | undefined): string[] {
  if (!entity) return [];
  const mt5 = resolveServers(entity, 'mt5');
  const mt4 = resolveServers(entity, 'mt4');
  return Array.from(new Set([...mt5.demo, ...mt5.live, ...mt4.demo, ...mt4.live]));
}
