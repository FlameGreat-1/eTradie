import {
  useLlmConnections, useActiveLlmConnection, useLlmProviders,
  useCreateLlmConnection, useActivateLlm, useDeactivateLlm, useDeleteLlmConnection,
} from '@/features/llm/api/llmConnections';
import { useState } from 'react';
import { Plus, Power, PowerOff, Trash2 } from 'lucide-react';

export default function LlmSection() {
  const { data: connections } = useLlmConnections();
  const { data: active } = useActiveLlmConnection();
  const { data: providers } = useLlmProviders();
  const createConn = useCreateLlmConnection();
  const activate = useActivateLlm();
  const deactivate = useDeactivateLlm();
  const deleteConn = useDeleteLlmConnection();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: '', api_key: '' });

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];
  const providerMap: Record<string, unknown> = providers ?? {};
  const providerList = Object.keys(providerMap);

  const handleCreate = async () => {
    await createConn.mutateAsync({
      provider: form.provider,
      api_key: form.api_key,
      activate: true,
    });
    setShowForm(false);
    setForm({ provider: '', api_key: '' });
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-content">API Key Connections</h3>
        <button onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white hover:bg-brand-dark transition-colors">
          <Plus size={12} /> Add Connection
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-4">
          {/* Provider — required */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-content">1. Select AI Provider</label>
            <select value={form.provider} onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content focus:outline-none focus:border-brand">
              <option value="">Choose a provider…</option>
              {providerList.map((p) => (
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
              ))}
            </select>
          </div>

          {/* API Key — required, shown after provider selected */}
          {form.provider && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-content">2. Paste your API Key</label>
              <input type="password" autoComplete="off" value={form.api_key}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder={`Enter your ${form.provider} API key`}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content
                           focus:outline-none focus:border-brand placeholder:text-content-muted" />
            </div>
          )}

          {/* Submit */}
          <button onClick={handleCreate} disabled={createConn.isPending || !form.provider || !form.api_key}
            className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white
                       hover:bg-brand-dark disabled:opacity-40 transition-colors">
            {createConn.isPending ? 'Connecting…' : 'Activate'}
          </button>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface-1 overflow-hidden">
        {conns.length === 0 && (
          <div className="p-8 text-center text-sm text-content-muted">No API Key connections configured yet</div>
        )}
        {conns.map((c) => {
          const id = String(c.id);
          const isActive = c.is_active === true || String(active?.id) === id;
          return (
            <div key={id} className="flex items-center justify-between px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
              <div className="flex items-center gap-3">
                {isActive && <span className="w-2 h-2 rounded-full bg-success" />}
                <div>
                  <span className="text-xs font-bold text-content">{String(c.provider)} / {String(c.model_name)}</span>
                  <span className="block text-[10px] text-content-muted">Temp: {String(c.temperature)}</span>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {isActive ? (
                  <button onClick={() => deactivate.mutate(id)} className="p-1.5 rounded text-warning hover:bg-surface-3 transition-colors" title="Deactivate">
                    <PowerOff size={14} />
                  </button>
                ) : (
                  <button onClick={() => activate.mutate(id)} className="p-1.5 rounded text-success hover:bg-surface-3 transition-colors" title="Activate">
                    <Power size={14} />
                  </button>
                )}
                <button onClick={() => deleteConn.mutate(id)} className="p-1.5 rounded text-danger hover:bg-surface-3 transition-colors" title="Delete">
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
