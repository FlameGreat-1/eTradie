import { useState } from 'react';
import {
  useBrokerConnections, useActiveBrokerConnection,
  useCreateBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import { Server, Check, ChevronRight, ChevronDown } from 'lucide-react';

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

interface Props { onComplete: () => void; }

export function BrokerStep({ onComplete }: Props) {
  const { data: connections } = useBrokerConnections();
  const { data: active } = useActiveBrokerConnection();
  const createConn = useCreateBrokerConnection();

  const [form, setForm] = useState<BrokerForm>(INITIAL_FORM);
  const [error, setError] = useState('');

  const alreadyConnected = !!active || (Array.isArray(connections) && connections.length > 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.name.trim()) { setError('Give your connection a name.'); return; }
    
    try {
      await createConn.mutateAsync({
        connection_type: form.connection_type,
        name: form.name,
        mt5_server: form.mt5_server,
        mt5_login: form.mt5_login,
        mt5_password: form.mt5_password,
        platform: form.platform,
      });
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
        <button onClick={onComplete} className="inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-6 py-3 text-sm font-semibold text-white dark:text-black hover:opacity-90">
          Continue <ChevronRight size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <Server className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Connect your broker</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Type</label>
            <div className="relative">
              <select
                value={form.connection_type}
                onChange={(e) => setForm((f) => ({ ...f, connection_type: e.target.value as BrokerForm['connection_type'] }))}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand transition-colors appearance-none">
                <option value="ea">ZeroMQ (EA)</option>
                <option value="metaapi">MetaAPI</option>
                <option value="hosted">Exoper</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none" size={14} strokeWidth={3} />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Connection Name</label>
            <input type="text" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="My MT5 Account" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
          </div>
          
          {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
            <div className="space-y-1">
              <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Platform</label>
                <div className="relative">
                  <select
                    value={form.platform}
                    onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value as 'mt4' | 'mt5' }))}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand appearance-none"
                  >
                    <option value="mt5">MetaTrader 5</option>
                    <option value="mt4">MetaTrader 4</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-content-faint pointer-events-none" size={14} strokeWidth={3} />
                </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Broker Server</label>
            <input type="text" value={form.mt5_server} onChange={(e) => setForm((f) => ({ ...f, mt5_server: e.target.value }))}
              placeholder="Exness-MT5Trial9" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Login ID</label>
            <input type="text" value={form.mt5_login} onChange={(e) => setForm((f) => ({ ...f, mt5_login: e.target.value }))}
              placeholder="12345678" className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
          </div>
          
          {(form.connection_type === 'metaapi' || form.connection_type === 'hosted') && (
            <div className="col-span-2 space-y-1">
              <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Trading Password</label>
              <input type="password" value={form.mt5_password}
                onChange={(e) => setForm((f) => ({ ...f, mt5_password: e.target.value }))}
                placeholder="••••••••"
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
            </div>
          )}
        </div>

        {error && <p className="text-[11px] text-red-500 text-center">{error}</p>}

        <button type="submit" disabled={createConn.isPending}
          className="w-full rounded-xl bg-black dark:bg-white p-3.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-50 transition-all active:scale-[0.98]">
          {createConn.isPending ? 'Connecting...' : 'Connect broker'}
        </button>
      </form>
    </div>
  );
}
