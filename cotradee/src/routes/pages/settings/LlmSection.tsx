import { useState } from 'react';
import {
  AlertCircle,
  Plus,
  Power,
  PowerOff,
  ShieldCheck,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  useActivateLlm,
  useActiveLlmConnection,
  useCreateLlmConnection,
  useDeactivateLlm,
  useDeleteLlmConnection,
  useLlmConnections,
  useLlmProviders,
} from '@/features/llm/api/llmConnections';
import { useTierGate } from '@/features/auth/hooks/useTierGate';

export default function LlmSection() {
  const { data: connections } = useLlmConnections();
  const { data: active } = useActiveLlmConnection();
  const { data: providers } = useLlmProviders();
  const createConn = useCreateLlmConnection();
  const activate = useActivateLlm();
  const deactivate = useDeactivateLlm();
  const deleteConn = useDeleteLlmConnection();

  const { tier, isProManaged, isProBYOK, isFree, copy, openUpgradeModal } =
    useTierGate();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: '', api_key: '' });

  // The Platform Key toggle is ON exactly when:
  //   - the user is pro_managed AND
  //   - no user-owned LLM connection is currently active.
  // The engine's _load_active_llm_connection treats 'no active row +
  // pro_managed' as the signal to fall back to the platform env-var key
  // (defense-in-depth there; this toggle is the matching UX surface).
  const platformKeyOn = isProManaged && !active;

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];
  const providerMap: Record<string, unknown> = providers ?? {};
  const providerList = Object.keys(providerMap);

  const platformKeyCopy = copy('platformKey');

  const handleCreate = async () => {
    await createConn.mutateAsync({
      provider: form.provider,
      api_key: form.api_key,
      activate: true,
    });
    setShowForm(false);
    setForm({ provider: '', api_key: '' });
  };

  const handleToggleClick = async () => {
    // Tier-aware behaviour for the Platform Key toggle.
    if (!isProManaged) {
      // The engine WILL reject any pro_byok or free user that tries to
      // run analysis with no active row, so we keep parity in the UX.
      openUpgradeModal();
      return;
    }

    // Pro Managed: toggling OFF means activating a user-owned connection
    // (the user must have one already — we don't auto-create here).
    // Toggling ON means deactivating whatever's currently active so the
    // engine falls through to the platform env-var key.
    if (platformKeyOn) {
      // Currently using platform key — nothing to toggle off without an
      // alternative connection. Open the 'add connection' form so the
      // user can attach a personal key first.
      setShowForm(true);
      return;
    }

    if (active && typeof active.id === 'string') {
      await deactivate.mutateAsync(active.id);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-content">API Key Connections</h3>
          {isProManaged ? (
            <p className="text-[11px] text-content-muted mt-1 flex items-center gap-1">
              <ShieldCheck size={12} className="text-brand" />
              Pro Managed: Platform AI is available. Toggle below or add a custom override.
            </p>
          ) : isProBYOK ? (
            <p className="text-[11px] text-warning mt-1 flex items-center gap-1">
              <AlertCircle size={12} />
              Pro BYOK: You must configure an API key to run analysis.
            </p>
          ) : (
            <p className="text-[11px] text-warning mt-1 flex items-center gap-1">
              <AlertCircle size={12} />
              Free Tier: You must configure an API key to run analysis.
            </p>
          )}
        </div>
        <button
          onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white hover:bg-brand-dark transition-colors"
        >
          <Plus size={12} /> Add Connection
        </button>
      </div>

      {/* Platform Key toggle card. Visible to every tier; only pro_managed can toggle ON. */}
      <div
        className={`rounded-xl border p-4 transition-colors ${
          isProManaged
            ? 'border-brand/30 bg-brand/5'
            : 'border-border bg-surface-1'
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-lg bg-brand/15 p-1.5">
              <Sparkles size={14} className="text-brand" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-semibold text-content">
                Use Platform AI Key
              </p>
              <p className="text-[11px] text-content-muted leading-relaxed">
                {isProManaged
                  ? 'Skip provider-key setup. The platform supplies and manages the API key for you.'
                  : platformKeyCopy.body}
              </p>
            </div>
          </div>

          <button
            type="button"
            role="switch"
            aria-checked={platformKeyOn}
            aria-label={`Use Platform AI Key (${tier})`}
            onClick={handleToggleClick}
            disabled={deactivate.isPending}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full border transition-colors
                       focus:outline-none focus:ring-2 focus:ring-brand/60 disabled:opacity-50
                       ${
                         platformKeyOn
                           ? 'bg-brand border-brand'
                           : isProManaged
                           ? 'bg-surface-2 border-border'
                           : 'bg-surface-2 border-border cursor-not-allowed'
                       }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform ${
                platformKeyOn ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {!isProManaged && (
          <div className="mt-3 flex items-center justify-end">
            <button
              type="button"
              onClick={openUpgradeModal}
              className="text-[11px] font-semibold text-brand hover:text-brand-dark transition-colors"
            >
              {isFree ? 'Upgrade to Pro →' : 'Upgrade to Pro Managed →'}
            </button>
          </div>
        )}
      </div>

      {showForm && (
        <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-content">
              1. Select AI Provider
            </label>
            <select
              value={form.provider}
              onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content focus:outline-none focus:border-brand"
            >
              <option value="">Choose a provider…</option>
              {providerList.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {form.provider && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-content">
                2. Paste your API Key
              </label>
              <input
                type="password"
                autoComplete="off"
                value={form.api_key}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder={`Enter your ${form.provider} API key`}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-content
                           focus:outline-none focus:border-brand placeholder:text-content-muted"
              />
            </div>
          )}

          <button
            onClick={handleCreate}
            disabled={createConn.isPending || !form.provider || !form.api_key}
            className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white
                       hover:bg-brand-dark disabled:opacity-40 transition-colors"
          >
            {createConn.isPending ? 'Connecting…' : 'Activate'}
          </button>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface-1 overflow-hidden">
        {conns.length === 0 && (
          <div className="p-8 text-center text-sm text-content-muted">
            No API Key connections configured yet
          </div>
        )}
        {conns.map((c) => {
          const id = String(c.id);
          const isActive = c.is_active === true || String(active?.id) === id;
          return (
            <div
              key={id}
              className="flex items-center justify-between px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isActive && <span className="w-2 h-2 rounded-full bg-success" />}
                <div>
                  <span className="text-xs font-bold text-content">
                    {String(c.provider)} / {String(c.model_name)}
                  </span>
                  <span className="block text-[10px] text-content-muted">
                    Temp: {String(c.temperature)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {isActive ? (
                  <button
                    onClick={() => deactivate.mutate(id)}
                    className="p-1.5 rounded text-warning hover:bg-surface-3 transition-colors"
                    title="Deactivate"
                  >
                    <PowerOff size={14} />
                  </button>
                ) : (
                  <button
                    onClick={() => activate.mutate(id)}
                    className="p-1.5 rounded text-success hover:bg-surface-3 transition-colors"
                    title="Activate"
                  >
                    <Power size={14} />
                  </button>
                )}
                <button
                  onClick={() => deleteConn.mutate(id)}
                  className="p-1.5 rounded text-danger hover:bg-surface-3 transition-colors"
                  title="Delete"
                >
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
