import { useState } from 'react';
import {
  useBrokerConnections, useActiveBrokerConnection,
  useCreateBrokerConnection, useActivateBroker, useTestBrokerConnection, useDeleteBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import { Plus, Trash2, Zap, Check, AlertCircle, ChevronDown } from 'lucide-react';

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
    <div className="space-y-10 max-w-2xl">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Connectivity</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Broker Connections</h3>
        </div>
        <button onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all">
          <Plus size={14} strokeWidth={3} /> Add Connection
        </button>
      </div>

      {showForm && (
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Type</label>
              <div className="relative">
                <select
                  value={form.connection_type}
                  onChange={(e) => setForm((f) => ({ ...f, connection_type: e.target.value as BrokerForm['connection_type'] }))}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
                >
                  <option value="ea">ZeroMQ</option>
                  <option value="metaapi">MetaAPI</option>
                  <option value="hosted">Exoper</option>
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20 pointer-events-none" size={16} strokeWidth={3} />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Name</label>
              <input type="text" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="My Broker" className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
            </div>
            {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Platform</label>
                <div className="relative">
                  <select
                    value={form.platform}
                    onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value as 'mt4' | 'mt5' }))}
                    className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
                  >
                    <option value="mt5">MetaTrader 5</option>
                    <option value="mt4">MetaTrader 4</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20 pointer-events-none" size={16} strokeWidth={3} />
                </div>
              </div>
            )}
            {form.connection_type === 'ea' && (
              <>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">MT5 Server</label>
                  <input type="text" value={form.mt5_server} onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
                    placeholder="Exness-MT5Trial9" className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">MT5 Login</label>
                  <input type="text" value={form.mt5_login} onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
                    placeholder="12345678" className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
                </div>
              </>
            )}
            {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
              <>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Server Name</label>
                  <input type="text" value={form.mt5_server} onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
                    placeholder="Exness-MT5Trial9" className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Login</label>
                  <input type="text" value={form.mt5_login} onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
                    placeholder="12345678" className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">Password</label>
                  <input type="password" autoComplete="new-password" value={form.mt5_password}
                    onChange={(e) => setForm((f) => ({ ...f, mt5_password: e.target.value }))}
                    placeholder="Trading password"
                    className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none" />
                </div>
              </>
            )}
          </div>
          <button onClick={handleCreate} disabled={createConn.isPending}
            className="w-fit rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40">
            {createConn.isPending ? 'Creating…' : 'Create Connection'}
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] overflow-hidden shadow-sm">
        {conns.length === 0 && (
          <div className="p-10 text-center text-[11px] font-bold text-black/20 dark:text-white/20 italic">No broker connections configured</div>
        )}
        {conns.map((c) => {
          const id = String(c.id);
          const isActive = c.is_active === true || String(active?.id) === id;
          const subtitleParts = [String(c.connection_type), String(c.platform || 'mt5').toUpperCase()];
          if (c.mt5_server) subtitleParts.push(String(c.mt5_server));
          if (c.mt5_login) subtitleParts.push(String(c.mt5_login));
          const subtitle = subtitleParts.join(' · ');
          return (
            <div key={id} className="flex items-center justify-between px-6 py-4 border-b border-black/5 dark:border-white/5 last:border-b-0 hover:bg-black/5 dark:hover:bg-white/5 transition-all group">
              <div className="flex items-center gap-4">
                <div className={`w-3 h-3 rounded-full transition-all duration-500 ${isActive ? 'bg-green-500 shadow-lg shadow-green-500/40 scale-110' : 'bg-black/10 dark:bg-white/10 scale-90'}`} />
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-bold text-black dark:text-white tracking-tight">{String(c.name)}</span>
                  <span className="text-[10px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">{subtitle}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => testConn.mutate(id)}
                  className="p-2 rounded-lg text-black/20 dark:text-white/20 hover:text-brand hover:bg-brand/10 transition-all opacity-40 group-hover:opacity-100" title="Test">
                  {testConn.isPending ? <AlertCircle size={16} strokeWidth={3} className="animate-pulse" /> : <Check size={16} strokeWidth={3} />}
                </button>
                {!isActive && (
                  <button onClick={() => activateBroker.mutate(id)}
                    className="p-2 rounded-lg text-green-500 hover:bg-green-500/10 transition-all opacity-40 group-hover:opacity-100" title="Activate">
                    <Zap size={16} strokeWidth={3} />
                  </button>
                )}
                <button onClick={() => deleteConn.mutate(id)}
                  className="p-2 rounded-lg text-black/20 dark:text-white/20 hover:text-red-500 hover:bg-red-500/10 transition-all opacity-40 group-hover:opacity-100" title="Delete">
                  <Trash2 size={16} strokeWidth={3} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
