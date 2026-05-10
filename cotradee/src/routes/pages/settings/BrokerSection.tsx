import { useState } from 'react';
import {
  useBrokerConnections, useActiveBrokerConnection,
  useCreateBrokerConnection, useActivateBroker, useTestBrokerConnection, useDeleteBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import { Plus, Trash2, Zap, Check, AlertCircle } from 'lucide-react';

type BrokerForm = {
  connection_type: 'ea' | 'metaapi' | 'hosted';
  name: string;
  mt5_server: string;
  mt5_login: string;
  mt5_password: string;
  platform: 'mt4' | 'mt5';
};

const INITIAL_FORM: BrokerForm = {
  connection_type: 'ea',
  name: '',
  mt5_server: '',
  mt5_login: '',
  mt5_password: '',
  platform: 'mt5',
};

export default function BrokerSection() {
  const { data: connections } = useBrokerConnections();
  const { data: active } = useActiveBrokerConnection();
  const createConn = useCreateBrokerConnection();
  const activateBroker = useActivateBroker();
  const testConn = useTestBrokerConnection();
  const deleteConn = useDeleteBrokerConnection();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<BrokerForm>(INITIAL_FORM);

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];

  const handleCreate = async () => {
    // Build the payload to match exactly what the backend's
    // CreateBrokerConnectionRequest accepts. The backend ignores any
    // extra keys, but we still keep the wire format clean and minimal.
    //
    // EA connections: name only is needed by the backend; host/port/auth
    // come from server-side env vars. We forward MT5 server/login as
    // metadata labels so the user can identify the broker account this
    // connection corresponds to (these are stored in the DB row but do
    // not affect the ZeroMQ runtime, which uses the EA already attached
    // to the user's MT5 terminal).
    //
    // MetaAPI connections: mt5_server + mt5_login + mt5_password are the
    // user's broker credentials. The backend uses them to call
    // MetaApiProvisioner.provision_account() with the platform-level
    // MT5_METAAPI_TOKEN, which provisions the cloud account and stores
    // the returned metaapi_account_id automatically. The user never sees
    // or supplies the MetaAPI developer token or the cloud account ID.
    const payload: Record<string, unknown> = {
      connection_type: form.connection_type,
      name: form.name,
      mt5_server: form.mt5_server,
      mt5_login: form.mt5_login,
      mt5_password: form.mt5_password,
      platform: form.platform,
    };
    await createConn.mutateAsync(payload);
    setShowForm(false);
    setForm(INITIAL_FORM);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-content">Broker Connections</h3>
        <button onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white hover:bg-brand-dark transition-colors">
          <Plus size={12} /> Add Connection
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-content-muted">Type</label>
              <select
                value={form.connection_type}
                onChange={(e) => setForm((f) => ({ ...f, connection_type: e.target.value as BrokerForm['connection_type'] }))}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand">
                <option value="ea">ZeroMQ</option>
                <option value="metaapi">MetaAPI</option>
                <option value="hosted">Exoper</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-content-muted">Name</label>
              <input type="text" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="My Broker" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
            </div>
            {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
              <div className="space-y-1">
                <label className="text-xs text-content-muted">Platform</label>
                <select
                  value={form.platform}
                  onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value as 'mt4' | 'mt5' }))}
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand">
                  <option value="mt5">MetaTrader 5</option>
                  <option value="mt4">MetaTrader 4</option>
                </select>
              </div>
            )}
            {form.connection_type === 'ea' && (
              <>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">MT5 Server</label>
                  <input type="text" value={form.mt5_server} onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
                    placeholder="Exness-MT5Trial9" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">MT5 Login</label>
                  <input type="text" value={form.mt5_login} onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
                    placeholder="12345678" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
              </>
            )}
            {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
              <>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">Server Name</label>
                  <input type="text" value={form.mt5_server} onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
                    placeholder="Exness-MT5Trial9" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">Login</label>
                  <input type="text" value={form.mt5_login} onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
                    placeholder="12345678" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">Password</label>
                  <input type="password" autoComplete="new-password" value={form.mt5_password}
                    onChange={(e) => setForm((f) => ({ ...f, mt5_password: e.target.value }))}
                    placeholder="Trading password"
                    className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
              </>
            )}
          </div>
          <button onClick={handleCreate} disabled={createConn.isPending}
            className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white hover:bg-brand-dark disabled:opacity-50 transition-colors">
            {createConn.isPending ? 'Creating…' : 'Create Connection'}
          </button>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface-1 overflow-hidden">
        {conns.length === 0 && (
          <div className="p-8 text-center text-sm text-content-muted">No broker connections configured</div>
        )}
        {conns.map((c) => {
          const id = String(c.id);
          const isActive = c.is_active === true || String(active?.id) === id;
          // Show the broker info the user actually recognises (server + login)
          // instead of raw infrastructure values (ea_host or metaapi_account_id).
          const subtitleParts = [String(c.connection_type), String(c.platform || 'mt5').toUpperCase()];
          if (c.mt5_server) subtitleParts.push(String(c.mt5_server));
          if (c.mt5_login) subtitleParts.push(String(c.mt5_login));
          const subtitle = subtitleParts.join(' · ');
          return (
            <div key={id} className="flex items-center justify-between px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                {isActive && <span className="w-2 h-2 rounded-full bg-success" />}
                <div>
                  <span className="text-xs font-bold text-content">{String(c.name)}</span>
                  <span className="block text-[10px] text-content-muted">{subtitle}</span>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button onClick={() => testConn.mutate(id)}
                  className="p-1.5 rounded text-content-muted hover:text-brand hover:bg-surface-3 transition-colors" title="Test">
                  {testConn.isPending ? <AlertCircle size={14} /> : <Check size={14} />}
                </button>
                {!isActive && (
                  <button onClick={() => activateBroker.mutate(id)}
                    className="p-1.5 rounded text-success hover:bg-surface-3 transition-colors" title="Activate">
                    <Zap size={14} />
                  </button>
                )}
                <button onClick={() => deleteConn.mutate(id)}
                  className="p-1.5 rounded text-danger hover:bg-surface-3 transition-colors" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
