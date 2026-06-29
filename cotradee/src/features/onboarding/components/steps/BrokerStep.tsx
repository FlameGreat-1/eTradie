import { useEffect, useMemo, useState } from 'react';
import {
  useBrokerConnections,
  useActiveBrokerConnection,
  useCreateBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import {
  resolveServers,
  type BrandRecord,
  type EntityRecord,
  type PlatformId,
} from '@/features/broker/api/brokerRegistry';
import { Server, Check, ChevronRight, ChevronDown, ArrowLeft } from 'lucide-react';

type ConnectionType = 'ea' | 'metaapi' | 'hosted';

type BrokerForm = {
  connection_type: ConnectionType;
  name: string;
  mt5_server: string;
  mt5_login: string;
  mt5_password: string;
  platform: PlatformId;
  entity_id: string;
};

const INITIAL_FORM: BrokerForm = {
  connection_type: 'hosted',
  name: '',
  mt5_server: '',
  mt5_login: '',
  mt5_password: '',
  platform: 'mt5',
  entity_id: '',
};

interface Props {
  brand: BrandRecord | null;
  onBack: () => void;
  onComplete: () => void;
}

export function BrokerStep({ brand, onBack, onComplete }: Props) {
  const { data: connections } = useBrokerConnections();
  const { data: active } = useActiveBrokerConnection();
  const createConn = useCreateBrokerConnection();

  const [form, setForm] = useState<BrokerForm>(() => {
    const initial: BrokerForm = { ...INITIAL_FORM };
    if (brand) {
      if (brand.is_metaapi_only) initial.connection_type = 'metaapi';
      if (brand.mt5_supported) initial.platform = 'mt5';
      else if (brand.mt4_supported) initial.platform = 'mt4';
      if (brand.entities.length === 1) initial.entity_id = brand.entities[0].entity_id;
      initial.name = `My ${brand.display_name} Account`;
    }
    return initial;
  });
  const [error, setError] = useState('');

  useEffect(() => {
    if (!brand) onBack();
  }, [brand, onBack]);

  useEffect(() => {
    if (!brand) return;
    setForm((f) => {
      const next = { ...f };
      if (brand.entities.length === 1) {
        next.entity_id = brand.entities[0].entity_id;
      } else if (!brand.entities.some((e) => e.entity_id === f.entity_id)) {
        next.entity_id = '';
      }
      const supportsCurrent =
        f.platform === 'mt5' ? brand.mt5_supported : brand.mt4_supported;
      if (!supportsCurrent) {
        next.platform = brand.mt5_supported ? 'mt5' : 'mt4';
      }
      if (!f.name?.trim()) {
        next.name = `My ${brand.display_name} Account`;
      }
      next.mt5_server = '';
      if (brand.is_metaapi_only && f.connection_type !== 'metaapi') {
        next.connection_type = 'metaapi';
      } else if (!brand.is_metaapi_only && f.connection_type === 'metaapi') {
        // Option to reset if needed, but not strictly necessary since Exoper supports both technically.
      }
      return next;
    });
  }, [brand]);

  const alreadyConnected =
    !!active || (Array.isArray(connections) && connections.length > 0);

  const selectedEntity: EntityRecord | null = useMemo(() => {
    if (!brand) return null;
    if (!form.entity_id) {
      return brand.entities.length === 1 ? brand.entities[0] : null;
    }
    return brand.entities.find((e) => e.entity_id === form.entity_id) ?? null;
  }, [brand, form.entity_id]);

  const serverLists = useMemo(
    () => resolveServers(selectedEntity, form.platform),
    [selectedEntity, form.platform],
  );

  const availablePlatforms = useMemo<PlatformId[]>(() => {
    if (!brand) return ['mt5', 'mt4'];
    const out: PlatformId[] = [];
    if (brand.mt5_supported) out.push('mt5');
    if (brand.mt4_supported) out.push('mt4');
    return out.length > 0 ? out : ['mt5'];
  }, [brand]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!brand || !selectedEntity) {
      setError('Pick a broker first.');
      return;
    }
    if (!form.name.trim()) {
      setError('Give your connection a name.');
      return;
    }
    if (!form.mt5_login.trim()) {
      setError('Enter your broker account login.');
      return;
    }
    if (!form.mt5_password.trim()) {
      setError('Enter your broker trading password.');
      return;
    }
    if (!form.mt5_server.trim()) {
      setError('Select your broker server.');
      return;
    }

    const payload: Record<string, unknown> = {
      connection_type: form.connection_type,
      name: form.name.trim(),
      mt5_server: form.mt5_server,
      mt5_login: form.mt5_login,
      mt5_password: form.mt5_password,
      platform: form.platform,
    };

    if (form.connection_type === 'hosted') {
      payload.broker_id = brand.brand_id;
      payload.entity_id = selectedEntity.entity_id;
    }

    try {
      await createConn.mutateAsync(payload);
      onComplete();
    } catch {
      setError('Connection failed. Please check your credentials.');
    }
  };

  if (alreadyConnected) {
    return (
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10">
          <Check className="h-8 w-8 text-success" />
        </div>
        <h2 className="text-xl font-bold text-content">Broker connected</h2>
        <button
          onClick={onComplete}
          className="inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-6 py-3 text-sm font-semibold text-white dark:text-black hover:opacity-90"
        >
          Continue <ChevronRight size={16} />
        </button>
      </div>
    );
  }

  if (!brand) return null;

  const requiresPassword =
    form.connection_type === 'metaapi' || form.connection_type === 'hosted';

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-6">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <Server className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Connect your broker</h2>
        <p className="mt-2 text-sm text-content-secondary">
          <span className="font-semibold text-content">{brand.display_name}</span>
          {brand.entities.length === 1 && (
            <span className="text-content-muted"> · {brand.entities[0].display_name}</span>
          )}
        </p>
        <button
          type="button"
          onClick={onBack}
          className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-content-muted hover:text-content"
        >
          <ArrowLeft size={12} /> Change broker
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
              Type
            </label>
            <div className="relative">
              <select
                value={form.connection_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, connection_type: e.target.value as ConnectionType }))
                }
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand transition-colors appearance-none"
              >
                {!brand?.is_metaapi_only && <option value="hosted">Exoper</option>}
                <option value="metaapi">MetaAPI</option>
                <option value="ea">ZeroMQ (EA)</option>
              </select>
              <ChevronDown
                className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none"
                size={14}
                strokeWidth={3}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
              Connection Name
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="My MT5 Account"
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand"
            />
          </div>

          {brand.entities.length > 1 && (
            <div className="col-span-2 space-y-1">
              <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
                Legal Entity
              </label>
              <div className="relative">
                <select
                  value={form.entity_id}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, entity_id: e.target.value, mt5_server: '' }))
                  }
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand appearance-none"
                >
                  <option value="" disabled>
                    Select an entity…
                  </option>
                  {brand.entities.map((e) => (
                    <option key={e.entity_id} value={e.entity_id}>
                      {e.display_name}
                      {e.regulator && e.regulator !== 'unknown' ? ` (${e.regulator})` : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none"
                  size={14}
                  strokeWidth={3}
                />
              </div>
            </div>
          )}

          {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
            <div className="space-y-1">
              <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
                Platform
              </label>
              <div className="relative">
                <select
                  value={form.platform}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, platform: e.target.value as PlatformId, mt5_server: '' }))
                  }
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand appearance-none"
                >
                  {availablePlatforms.includes('mt5') && (
                    <option value="mt5">MetaTrader 5</option>
                  )}
                  {availablePlatforms.includes('mt4') && (
                    <option value="mt4">MetaTrader 4</option>
                  )}
                </select>
                <ChevronDown
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none"
                  size={14}
                  strokeWidth={3}
                />
              </div>
            </div>
          )}

          <div
            className={`${
              form.connection_type === 'metaapi' || form.connection_type === 'hosted'
                ? 'col-span-1'
                : 'col-span-2'
            } space-y-1`}
          >
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
              Broker Server
            </label>
            <div className="relative">
              <select
                value={form.mt5_server}
                onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
                disabled={!selectedEntity}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="" disabled>
                  {selectedEntity ? 'Select a server…' : 'Pick an entity first'}
                </option>
                {serverLists.demo.length > 0 && (
                  <optgroup label="Demo">
                    {serverLists.demo.map((s) => (
                      <option key={`d-${s}`} value={s}>
                        {s}
                      </option>
                    ))}
                  </optgroup>
                )}
                {serverLists.live.length > 0 && (
                  <optgroup label="Live">
                    {serverLists.live.map((s) => (
                      <option key={`l-${s}`} value={s}>
                        {s}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
              <ChevronDown
                className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none"
                size={14}
                strokeWidth={3}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
              Login ID
            </label>
            <input
              type="text"
              value={form.mt5_login}
              onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
              placeholder="12345678"
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand"
            />
          </div>

          {requiresPassword && (
            <div className="col-span-2 space-y-1">
              <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
                Trading Password
              </label>
              <input
                type="password"
                value={form.mt5_password}
                onChange={(e) => setForm((f) => ({ ...f, mt5_password: e.target.value }))}
                placeholder="••••••••"
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand"
              />
            </div>
          )}
        </div>

        {error && <p className="text-[11px] text-danger text-center">{error}</p>}

        <button
          type="submit"
          disabled={createConn.isPending}
          className="w-full rounded-xl bg-black dark:bg-white p-3.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-50 transition-all active:scale-[0.98]"
        >
          {createConn.isPending ? 'Connecting…' : 'Connect broker'}
        </button>
      </form>
    </div>
  );
}
