import { useState, useEffect } from 'react';
import { Settings, Cpu, Key, Link2, Save, RefreshCw, ChevronDown } from 'lucide-react';
import { useProcessorConfig, useProcessorModels, useUpdateProcessorConfig } from '../api/admin';

export function AdminProcessorConfigPanel() {
  const configQuery = useProcessorConfig();
  const modelsQuery = useProcessorModels();
  const updateMutation = useUpdateProcessorConfig();

  const [formData, setFormData] = useState({
    llm_provider: '',
    model_name: '',
    temperature: 0,
    max_output_tokens: 0,
    api_key: '',
    api_base_url: '',
  });

  const [updateMessage, setUpdateMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    if (configQuery.data) {
      setFormData(prev => ({
        ...prev,
        llm_provider: prev.llm_provider || configQuery.data.llm_provider,
        model_name: prev.model_name || configQuery.data.model_name,
        temperature: prev.temperature || configQuery.data.temperature,
        max_output_tokens: prev.max_output_tokens || configQuery.data.max_output_tokens,
      }));
    }
  }, [configQuery.data]);

  if (configQuery.isLoading || modelsQuery.isLoading) {
    return <div className="p-8 text-center text-sm text-content-muted">Loading processor config...</div>;
  }

  if (configQuery.isError || modelsQuery.isError) {
    return null;
  }

  const modelsData = modelsQuery.data;
  if (!modelsData) return null;

  const handleProviderChange = (newProvider: string) => {
    let newModel = '';
    if (newProvider === 'self_hosted') {
      newModel = modelsData.self_hosted?.default_model || 'default';
    } else {
      newModel = modelsData.providers?.[newProvider]?.default_model || '';
    }
    setFormData({ ...formData, llm_provider: newProvider, model_name: newModel });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setUpdateMessage({ type: '', text: '' });

    const payload: any = {
      llm_provider: formData.llm_provider,
      model_name: formData.model_name,
      temperature: Number(formData.temperature),
      max_output_tokens: Number(formData.max_output_tokens),
    };
    if (formData.api_key) payload.api_key = formData.api_key;
    if (formData.api_base_url) payload.api_base_url = formData.api_base_url;

    updateMutation.mutate(payload, {
      onSuccess: () => {
        setUpdateMessage({ type: 'success', text: 'Processor configuration updated successfully. The engine has been hot-swapped.' });
        setFormData(prev => ({ ...prev, api_key: '' })); // clear the key field
      },
      onError: (err: any) => {
        setUpdateMessage({ type: 'error', text: err?.response?.data?.detail || 'Failed to update configuration.' });
      }
    });
  };

  const currentProviderInfo = formData.llm_provider === 'self_hosted'
    ? modelsData.self_hosted
    : modelsData.providers?.[formData.llm_provider];

  const acceptsCustom = currentProviderInfo?.accepts_custom;
  const requiresApiBase = currentProviderInfo?.requires_api_base_url;

  return (
    <div className="rounded-2xl border border-brand/20 bg-brand/5 p-6 shadow-sm mb-10 max-w-2xl">
      <div className="flex items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 rounded-xl bg-brand/10 p-2 border border-brand/20 shadow-sm">
            <Cpu size={16} className="text-brand" strokeWidth={2.5} />
          </div>
          <div className="space-y-1">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-brand mb-1">
              Global LLM Routing
            </h3>
            <p className="text-sm font-bold text-black dark:text-white tracking-tight">
              Processor Configuration
            </p>
          </div>
        </div>
        <button
          onClick={() => { configQuery.refetch(); modelsQuery.refetch(); }}
          disabled={configQuery.isFetching || modelsQuery.isFetching}
          className="rounded-xl bg-black dark:bg-white px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-sm transition-all disabled:opacity-40 flex items-center gap-2"
        >
          <RefreshCw size={12} strokeWidth={3} className={configQuery.isFetching || modelsQuery.isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <p className="mt-6 mb-6 text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
        This panel controls the global LLM router. Updating these settings performs a zero-downtime hot-swap of the system's core intelligence processor. 
        Changes made here affect all users who do not have a custom BYOK connection active.
      </p>

      {updateMessage.text && (
        <div className={`p-4 rounded-lg text-sm border ${updateMessage.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-red-500/10 border-red-500/20 text-red-500'}`}>
          {updateMessage.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">
              LLM Provider
            </label>
            <div className="relative">
              <select
                value={formData.llm_provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
              >
                {Object.keys(modelsData.providers || {}).map((p) => (
                  <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                ))}
                <option value="self_hosted">Self Hosted (Local/vLLM)</option>
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20 pointer-events-none" size={16} strokeWidth={3} />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">
              Model Name
            </label>
            {acceptsCustom ? (
              <input
                type="text"
                required
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                placeholder={currentProviderInfo?.note || "e.g. meta-llama/Llama-3-70b-instruct"}
              />
            ) : (
              <div className="relative">
                <select
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
                >
                  {(currentProviderInfo?.models || []).map((m: string) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20 pointer-events-none" size={16} strokeWidth={3} />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">
              Temperature
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="2"
              required
              value={formData.temperature}
              onChange={(e) => setFormData({ ...formData, temperature: Number(e.target.value) })}
              className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">
              Max Output Tokens
            </label>
            <input
              type="number"
              step="1"
              min="1"
              required
              value={formData.max_output_tokens}
              onChange={(e) => setFormData({ ...formData, max_output_tokens: Number(e.target.value) })}
              className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none"
            />
          </div>
        </div>

        <div className="border-t border-brand/10 pt-6 mt-6 space-y-6">
          <h4 className="text-sm font-bold text-black dark:text-white flex items-center gap-2">
            <Key size={14} className="text-brand" strokeWidth={2.5} />
            Credentials Override
          </h4>
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
            Leave the API Key blank to continue using the existing securely stored key for this provider. 
            Only fill this out if you need to rotate the key.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">
                API Key (Optional)
              </label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                placeholder="••••••••••••••••••••••••"
              />
            </div>

            {requiresApiBase && (
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1 flex items-center gap-1.5">
                  <Link2 size={12} strokeWidth={2.5} /> API Base URL
                </label>
                <input
                  type="url"
                  value={formData.api_base_url}
                  onChange={(e) => setFormData({ ...formData, api_base_url: e.target.value })}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                  placeholder="http://localhost:8000/v1"
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-end pt-4 mt-6">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="rounded-xl bg-black dark:bg-white px-6 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-black/10 dark:shadow-white/10"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
}
