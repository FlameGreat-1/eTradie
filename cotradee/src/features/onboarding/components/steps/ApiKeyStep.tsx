import { useState } from 'react';
import {
  useActiveLlmConnection,
  useCreateLlmConnection,
  useLlmProviders,
} from '@/features/llm/api/llmConnections';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { Check, ChevronRight, Key, Loader2, ShieldCheck, Sparkles, ChevronDown } from 'lucide-react';

interface Props {
  onComplete: () => void;
}

export function ApiKeyStep({ onComplete }: Props) {
  const { data: active } = useActiveLlmConnection();
  const { data: providers } = useLlmProviders();
  const createConn = useCreateLlmConnection();
  const { isProManaged } = useTierGate();

  const [form, setForm] = useState({ model_id: '', provider: '', api_key: '' });
  const [error, setError] = useState('');

  const isDone = !!active || isProManaged;

  if (isDone) {
    return (
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10">
          {isProManaged && !active
            ? <Sparkles className="h-8 w-8 text-brand" />
            : <Check className="h-8 w-8 text-success" />
          }
        </div>
        <div>
          <h2 className="text-xl font-bold text-content">
            {isProManaged && !active ? 'Platform AI active' : 'API key connected'}
          </h2>
          <p className="mt-2 text-sm text-content-secondary">
            {isProManaged && !active
              ? 'Your Pro Managed plan includes platform AI. No key needed.'
              : 'Your AI provider is linked and ready for analysis.'
            }
          </p>
        </div>
        <button type="button" onClick={onComplete}
          className="inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-black hover:bg-white/90 transition-colors duration-200">
          Continue <ChevronRight size={16} />
        </button>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.model_id) { setError('Select a model first.'); return; }
    if (!form.api_key.trim()) { setError('Paste your API key.'); return; }

    try {
      await createConn.mutateAsync({
        provider: form.provider,
        model_name: form.model_id,
        api_key: form.api_key,
        activate: true,
      });
      onComplete();
    } catch {
      setError('Failed to connect. Please check your API key and try again.');
    }
  };

  const catalog = Array.isArray((providers as any)?.catalog) ? (providers as any).catalog : [];

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
          <Key className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Add your AI key</h2>
        <p className="mt-2 text-sm text-content-secondary leading-relaxed">
          Exoper uses your OpenAI, Anthropic, or Google key for market analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Select model</label>
          <div className="relative">
            <select
              value={form.model_id}
              onChange={(e) => {
                const modelId = e.target.value;
                const model = catalog.find((m: any) => m.id === modelId);
                setForm((f) => ({ ...f, model_id: modelId, provider: model?.provider || '' }));
              }}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-content
                         focus:outline-none focus:border-white/30 transition-colors duration-200 appearance-none"
            >
              <option value="" disabled hidden>Choose a model…</option>
              {catalog.map((m: any) => (
                <option key={m.id} value={m.id}>{m.display_name}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/20 pointer-events-none" size={16} strokeWidth={3} />
          </div>
        </div>

        {form.model_id && (
          <div className="space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
              {form.provider.toUpperCase()} API Key
            </label>
            <input
              type="password"
              autoComplete="off"
              value={form.api_key}
              onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
              placeholder="sk-..."
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-content
                         placeholder:text-content-muted/50 focus:outline-none focus:border-white/30
                         transition-colors duration-200"
            />
          </div>
        )}

        {error && (
          <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</p>
        )}

        <button
          type="submit"
          disabled={createConn.isPending || !form.model_id || !form.api_key}
          className="w-full rounded-xl bg-white px-4 py-3.5 text-sm font-semibold text-black
                     hover:bg-white/90 disabled:opacity-50 transition-colors duration-200
                     flex items-center justify-center gap-2"
        >
          {createConn.isPending ? (
            <><Loader2 size={16} className="animate-spin" /> Connecting…</>
          ) : (
            <>Activate key <ChevronRight size={16} /></>
          )}
        </button>

        <div className="flex items-center justify-center gap-2 pt-2 text-[11px] text-content-muted">
          <ShieldCheck size={12} />
          <span>Your key is encrypted and never shared.</span>
        </div>
      </form>
    </div>
  );
}
