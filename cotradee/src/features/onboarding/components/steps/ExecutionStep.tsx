import { useEffect, useState } from 'react';
import { useExecutionSettings, useUpdateExecutionSettings } from '@/features/execution/api/brokerAccount';
import { ChevronRight, Settings2, ShieldCheck } from 'lucide-react';

interface Props { onComplete: () => void; }

export function ExecutionStep({ onComplete }: Props) {
  const { data: settings } = useExecutionSettings();
  const updateSettings = useUpdateExecutionSettings();
  const [form, setForm] = useState({ execution_mode: 'AUTO', max_concurrent_trades: 3, daily_loss_limit_pct: 3.0 });

  useEffect(() => {
    if (settings) {
      setForm({
        execution_mode: settings.execution_mode || 'AUTO',
        max_concurrent_trades: settings.max_concurrent_trades ?? 3,
        daily_loss_limit_pct: settings.daily_loss_limit_pct ?? 3.0
      });
    }
  }, [settings]);

  const handleSave = async () => {
    try {
      await updateSettings.mutateAsync(form);
      onComplete();
    } catch { /* */ }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <Settings2 className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Risk & Execution</h2>
        <p className="mt-2 text-sm text-content-secondary leading-relaxed">
          Configure how the AI interacts with your broker account.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-surface-2 p-6 space-y-6">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Mode</label>
            <select
              value={form.execution_mode}
              onChange={(e) => setForm(f => ({ ...f, execution_mode: e.target.value }))}
              className="w-full rounded-xl border border-border bg-surface-3 px-4 py-3 text-sm text-content focus:outline-none focus:border-brand"
            >
              <option value="AUTO">Automatic</option>
              <option value="MANUAL">Manual Approval</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Max Concurrent Trades</label>
            <input
              type="number"
              value={form.max_concurrent_trades}
              onChange={(e) => setForm(f => ({ ...f, max_concurrent_trades: Number(e.target.value) }))}
              className="w-full rounded-xl border border-border bg-surface-3 px-4 py-3 text-sm text-content focus:outline-none focus:border-brand"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-content-muted uppercase font-bold tracking-wider">Daily Loss Limit (%)</label>
            <input
              type="number"
              step="0.1"
              value={form.daily_loss_limit_pct}
              onChange={(e) => setForm(f => ({ ...f, daily_loss_limit_pct: Number(e.target.value) }))}
              className="w-full rounded-xl border border-border bg-surface-3 px-4 py-3 text-sm text-content focus:outline-none focus:border-brand"
            />
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={updateSettings.isPending}
          className="w-full rounded-xl bg-black dark:bg-white p-3.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          {updateSettings.isPending ? 'Saving...' : <>Save configuration <ChevronRight size={16} /></>}
        </button>

        <div className="flex items-center justify-center gap-2 pt-2 text-[11px] text-content-muted">
          <ShieldCheck size={12} />
          <span>These limits are enforced by the Execution Engine.</span>
        </div>
      </div>
    </div>
  );
}
