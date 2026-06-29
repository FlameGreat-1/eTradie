import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

export type PlatformId = 'mt4' | 'mt5';
export type InstallerPackaging = 'unified' | 'per_entity' | 'none' | 'unknown';
export type BrandStatus = 'active' | 'pending_bake' | 'unsupported_mt5' | 'inactive';

export interface ServerLists {
  demo: string[];
  live: string[];
}

export interface PlatformConfig {
  acquisition_url?: string | null;
  bundle_r2_path: string;
  bundle_sha256: string;
  verified_on?: string | null;
  servers: ServerLists;
}

export interface EntityRecord {
  entity_id: string;
  display_name: string;
  regulator?: string | null;
  platforms: Partial<Record<PlatformId, PlatformConfig>>;
}

export interface BrandRecord {
  brand_id: string;
  display_name: string;
  official_website: string;
  mt5_supported: boolean;
  mt4_supported: boolean;
  installer_packaging: InstallerPackaging;
  status: BrandStatus;
  notes?: string | null;
  is_metaapi_only?: boolean;
  entities: EntityRecord[];
}

export interface BrokerRegistryResponse {
  brands: BrandRecord[];
}

export function useBrokerRegistry() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ['broker', 'registry'],
    queryFn: async (): Promise<BrandRecord[]> => {
      const { data } = await api.engine.get<BrokerRegistryResponse>('/api/broker/registry');
      return data?.brands ?? [];
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

export function useMetaApiBrokers(query: string) {
  const { isAuthenticated } = useAuth();
  const trimmed = query.trim();
  const enabled = isAuthenticated && trimmed.length >= 2;

  return useQuery({
    queryKey: ['broker', 'metaapi', trimmed],
    queryFn: async (): Promise<BrandRecord[]> => {
      const { data } = await api.engine.get<BrokerRegistryResponse>(
        `/api/broker/metaapi/servers?q=${encodeURIComponent(trimmed)}`
      );
      return data?.brands ?? [];
    },
    enabled,
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
    refetchOnWindowFocus: false,
  });
}

export function findEntity(brand: BrandRecord, entityId: string): EntityRecord | null {
  return brand.entities.find((e) => e.entity_id === entityId) ?? null;
}

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

export function resolveAllServersForEntity(entity: EntityRecord | null | undefined): string[] {
  if (!entity) return [];
  const mt5 = resolveServers(entity, 'mt5');
  const mt4 = resolveServers(entity, 'mt4');
  return Array.from(new Set([...mt5.demo, ...mt5.live, ...mt4.demo, ...mt4.live]));
}
