import { useState } from 'react';
import {
  AlertCircle,
  Plus,
  Power,
  PowerOff,
  ShieldCheck,
  Sparkles,
  Trash2,
  ChevronDown,
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
import { useAuth, isAdmin } from '@/features/auth';

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
  const { user } = useAuth();
  const admin = isAdmin(user);

  // The Platform Key toggle is available to admins and Pro Managed users.
  // Backend parity: auth.Config.LLMQuotaPolicyForTier maps "admin" to the
  // same managed-tier policy as "pro_managed", and the engine's
  // _load_active_llm_connection falls through to the platform env-var
  // key whenever no user-owned connection is active for an admin or a
  // pro_managed user. Free + pro_byok users still cannot use the
  // platform key (the engine rejects it for them) so the toggle stays
  // locked behind the upgrade prompt for those tiers.
  const platformKeyAvailable = admin || isProManaged;

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: '', model_id: '', api_key: '' });

  // The Platform Key toggle is ON exactly when:
  //   - the user is permitted to use it (admin or pro_managed) AND
  //   - no user-owned LLM connection is currently active.
  const platformKeyOn = platformKeyAvailable && !active;

  const conns: Record<string, unknown>[] = Array.isArray(connections) ? connections : [];
  const providerMap: Record<string, unknown> = providers ?? {};

  const platformKeyCopy = copy('platformKey');

  const handleCreate = async () => {
    await createConn.mutateAsync({
      provider: form.provider,
      model_name: form.model_id,
      api_key: form.api_key,
      activate: true,
    });
    setShowForm(false);
    setForm({ provider: '', model_id: '', api_key: '' });
  };

  const handleToggleClick = async () => {
    // Tier-aware behaviour for the Platform Key toggle.
    if (!platformKeyAvailable) {
      // The engine WILL reject any pro_byok or free user that tries to
      // run analysis on the platform key, so we keep parity in the UX.
      openUpgradeModal();
      return;
    }

    // Admin / Pro Managed: toggling OFF means activating a user-owned
    // connection (the user must have one already — we don't auto-create
    // here). Toggling ON means deactivating whatever's currently active
    // so the engine falls through to the platform env-var key.
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
    <div className="space-y-10 max-w-2xl">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Intelligence</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">API Key Connections</h3>
          {admin ? (
            <p className="text-[11px] font-bold text-black/40 dark:text-white/40 mt-1 flex items-center gap-1.5">
              <ShieldCheck size={12} className="text-brand" strokeWidth={3} />
              Admin: Platform AI is available. Toggle below or add a custom override.
            </p>
          ) : isProManaged ? (
            <p className="text-[11px] font-bold text-black/40 dark:text-white/40 mt-1 flex items-center gap-1.5">
              <ShieldCheck size={12} className="text-brand" strokeWidth={3} />
              Pro Managed: Platform AI is available. Toggle below or add a custom override.
            </p>
          ) : isProBYOK ? (
            <p className="text-[11px] font-bold text-yellow-500/80 mt-1 flex items-center gap-1.5">
              <AlertCircle size={12} strokeWidth={3} />
              Pro BYOK: You must configure an API key to run analysis.
            </p>
          ) : (
            <p className="text-[11px] font-bold text-yellow-500/80 mt-1 flex items-center gap-1.5">
              <AlertCircle size={12} strokeWidth={3} />
              Free Tier: You must configure an API key to run analysis.
            </p>
          )}
        </div>
        <button
          onClick={() => setShowForm((p) => !p)}
          className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
        >
          <Plus size={14} strokeWidth={3} /> Add Connection
        </button>
      </div>

      <div
        className={`rounded-2xl border p-6 transition-all shadow-sm ${
          platformKeyAvailable
            ? 'border-brand/20 bg-brand/5'
            : 'border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02]'
        }`}
      >
        <div className="flex items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="mt-0.5 rounded-xl bg-brand/10 p-2 border border-brand/20 shadow-sm">
              <Sparkles size={16} className="text-brand" strokeWidth={2.5} />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-bold text-black dark:text-white tracking-tight">
                Use Platform AI Key
              </p>
              <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
                {platformKeyAvailable
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
            className={`relative inline-flex h-7 w-12 flex-shrink-0 items-center rounded-full border-2 transition-all duration-300
                       focus:outline-none disabled:opacity-20
                        ${
                          platformKeyOn
                            ? 'bg-brand/10 border-brand shadow-lg shadow-brand/10'
                            : platformKeyAvailable
                            ? 'bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10'
                            : 'bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10 cursor-not-allowed opacity-40'
                        }`}
          >
            <span
              className={`inline-block h-5 w-5 rounded-full shadow-md transform transition-all duration-300 ${
                platformKeyOn ? 'translate-x-6 bg-brand' : 'translate-x-1 bg-black/20 dark:bg-white/20'
              }`}
            />
          </button>
        </div>

        {!platformKeyAvailable && (
          <div className="mt-4 flex items-center justify-end">
            <button
              type="button"
              onClick={openUpgradeModal}
              className="text-[10px] font-black uppercase tracking-widest text-brand hover:opacity-80 transition-all"
            >
              {isFree ? 'Upgrade to Pro →' : 'Upgrade to Pro Managed →'}
            </button>
          </div>
        )}
      </div>

      {showForm && (
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 animate-in fade-in slide-in-from-top-2 duration-300 shadow-sm">
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">
              1. Select Enterprise Model
            </label>
            <div className="relative">
              <select
                value={form.model_id}
                onChange={(e) => {
                  const modelId = e.target.value;
                  const model = Array.isArray(providers?.catalog) 
                    ? providers.catalog.find((m: any) => m.id === modelId)
                    : null;
                  setForm((f) => ({ ...f, model_id: modelId, provider: model?.provider || '' }));
                }}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
              >
                <option value="" disabled hidden>Choose a model…</option>
                {Array.isArray(providers?.catalog) && providers.catalog.map((m: any) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20 pointer-events-none" size={16} strokeWidth={3} />
            </div>
          </div>

          {form.model_id && (
            <div className="space-y-2 animate-in fade-in slide-in-from-top-1 duration-300">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">
                2. Paste {form.provider.toUpperCase()} API Key
              </label>
              <input
                type="password"
                autoComplete="off"
                value={form.api_key}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder={`sk-...`}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
              />
            </div>
          )}

          <button
            onClick={handleCreate}
            disabled={createConn.isPending || !form.model_id || !form.api_key}
            className="w-fit rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
          >
            {createConn.isPending ? 'Connecting…' : 'Activate Connection'}
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] overflow-hidden shadow-sm">
        {conns.length === 0 && (
          <div className="p-10 text-center text-[11px] font-bold text-black/20 dark:text-white/20 italic italic">
            No API Key connections configured yet
          </div>
        )}
        {conns.map((c) => {
          const id = String(c.id);
          const isActive = c.is_active === true || String(active?.id) === id;
          return (
            <div
              key={id}
              className="flex items-center justify-between px-6 py-4 border-b border-black/5 dark:border-white/5 last:border-b-0 hover:bg-black/5 dark:hover:bg-white/5 transition-all group"
            >
              <div className="flex items-center gap-4">
                <div className={`w-3 h-3 rounded-full transition-all duration-500 ${isActive ? 'bg-green-500 shadow-lg shadow-green-500/40 scale-110' : 'bg-black/10 dark:bg-white/10 scale-90'}`} />
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-bold text-black dark:text-white tracking-tight">
                    {(providers?.catalog as any[])?.find(m => m.id === c.model_name)?.display_name || String(c.model_name)}
                  </span>
                  <span className="text-[10px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">
                    {String(c.provider).toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isActive ? (
                  <button
                    onClick={() => deactivate.mutate(id)}
                    className="p-2 rounded-lg text-red-500 hover:bg-red-500/10 transition-all opacity-40 group-hover:opacity-100"
                    title="Deactivate"
                  >
                    <PowerOff size={16} strokeWidth={3} />
                  </button>
                ) : (
                  <button
                    onClick={() => activate.mutate(id)}
                    className="p-2 rounded-lg text-green-500 hover:bg-green-500/10 transition-all opacity-40 group-hover:opacity-100"
                    title="Activate"
                  >
                    <Power size={16} strokeWidth={3} />
                  </button>
                )}
                <button
                  onClick={() => deleteConn.mutate(id)}
                  className="p-2 rounded-lg text-black/20 dark:text-white/20 hover:text-red-500 hover:bg-red-500/10 transition-all opacity-40 group-hover:opacity-100"
                  title="Delete"
                >
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
