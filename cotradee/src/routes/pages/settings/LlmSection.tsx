import {
  useLlmConnections, useActiveLlmConnection, useLlmProviders,
  useCreateLlmConnection, useActivateLlm, useDeactivateLlm, useDeleteLlmConnection,
} from '@/features/llm/api/llmConnections';
import { useState } from 'react';
import { Plus, Power, PowerOff, Trash2, ChevronDown } from 'lucide-react';

interface ProviderInfo {
  models: string[];
  default_model: string;
  accepts_custom?: boolean;
  requires_base_url?: boolean;
}

const DEFAULT_TEMPERATURE = 0.0;

export default function LlmSection() {
  const { data: connections } = useLlmConnections();
  const { data: active } = useActiveLlmConnection();
  const { data: providers } = useLlmProviders();
  const createConn = useCreateLlmConnection();
  const activate = useActivateLlm();
  const deactivate = useDeactivateLlm();
  const deleteConn = useDeleteLlmConnection();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: '', model: '', api_key: '', temperature: DEFAULT_TEMPERATURE });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];
  const providerMap: Record<string, ProviderInfo> = providers ?? {};
  const providerList = Object.keys(providerMap);

  /* When user picks a provider, auto-fill model + temperature */
  const handleProviderChange = (providerKey: string) => {
    const info = providerMap[providerKey];
    setForm((f) => ({
      ...f,
      provider: providerKey,
      model: info?.default_model ?? '',
      temperature: DEFAULT_TEMPERATURE,
    }));
  };

  const selectedProvider = providerMap[form.provider];
  const modelOptions: string[] = selectedProvider?.models ?? [];

  const handleCreate = async () => {
    await createConn.mutateAsync({
      provider: form.provider,
      model_name: form.model,
      api_key: form.api_key,
      temperature: Number(form.temperature),
      activate: true,
    });
    setShowForm(false);
    setForm({ provider: '', model: '', api_key: '', temperature: DEFAULT_TEMPERATURE });
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-content">AI Engine Connections</h3>
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
            <select value={form.provider} onChange={(e) => handleProviderChange(e.target.value)}
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

          {/* Pre-filled model info (read-only summary) */}
          {form.provider && form.model && (
            <div className="rounded-lg bg-surface-2 px-3 py-2.5 flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase tracking-wide text-content-muted">Model</span>
                <span className="block text-xs font-semibold text-content">{form.model}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wide text-content-muted">Temperature</span>
                <span className="block text-xs font-semibold text-content">{form.temperature}</span>
              </div>
              <button onClick={() => setShowAdvanced((p) => !p)}
                className="text-[10px] text-brand hover:underline flex items-center gap-0.5">
                {showAdvanced ? 'Hide' : 'Advanced'} <ChevronDown size={10} className={showAdvanced ? 'rotate-180' : ''} />
              </button>
            </div>
          )}

          {/* Advanced: editable model + temperature */}
          {showAdvanced && form.provider && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-content-muted">Model</label>
                {modelOptions.length > 0 ? (
                  <select value={form.model} onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand">
                    {modelOptions.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                ) : (
                  <input type="text" value={form.model} onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                    placeholder="Enter model name"
                    className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
                )}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-content-muted">Temperature</label>
                <input type="number" step="0.1" min="0" max="2" value={form.temperature}
                  onChange={(e) => setForm((f) => ({ ...f, temperature: parseFloat(e.target.value) || 0 }))}
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content focus:outline-none focus:border-brand" />
              </div>
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
          <div className="p-8 text-center text-sm text-content-muted">No AI connections configured yet</div>
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

