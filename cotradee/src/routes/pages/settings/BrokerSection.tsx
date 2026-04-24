import { useState } from 'react';
import {
  useBrokerConnections, useActiveBrokerConnection,
  useCreateBrokerConnection, useActivateBroker, useTestBrokerConnection, useDeleteBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import { Plus, Trash2, Zap, Check, AlertCircle } from 'lucide-react';

export default function BrokerSection() {
  const { data: connections } = useBrokerConnections();
  const { data: active } = useActiveBrokerConnection();
  const createConn = useCreateBrokerConnection();
  const activateBroker = useActivateBroker();
  const testConn = useTestBrokerConnection();
  const deleteConn = useDeleteBrokerConnection();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ connection_type: 'ea', name: '', meta_api_token: '', meta_api_account_id: '', mt5_server: '', mt5_login: '', mt5_password: '' });

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];

  const handleCreate = async () => {
    await createConn.mutateAsync(form);
    setShowForm(false);
    setForm({ connection_type: 'ea', name: '', meta_api_token: '', meta_api_account_id: '', mt5_server: '', mt5_login: '', mt5_password: '' });
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
              <select value={form.connection_type} onChange={(e) => setForm((f) => ({ ...f, connection_type: e.target.value }))}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand">
                <option value="ea">ZeroMQ (MT5 EA)</option>
                <option value="metaapi">MetaAPI Cloud</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-content-muted">Name</label>
              <input type="text" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="My MT5 Broker" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
            </div>
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
            {form.connection_type === 'metaapi' && (
              <>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">MetaAPI Token</label>
                  <input type="password" autoComplete="off" value={form.meta_api_token} onChange={(e) => setForm((f) => ({ ...f, meta_api_token: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-content-muted">Account ID</label>
                  <input type="text" value={form.meta_api_account_id} onChange={(e) => setForm((f) => ({ ...f, meta_api_account_id: e.target.value }))}
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
          return (
            <div key={id} className="flex items-center justify-between px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                {isActive && <span className="w-2 h-2 rounded-full bg-success" />}
                <div>
                  <span className="text-xs font-bold text-content">{String(c.name)}</span>
                  <span className="block text-[10px] text-content-muted">{String(c.connection_type)} · {String(c.ea_host ?? c.metaapi_account_id ?? '')}</span>
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
