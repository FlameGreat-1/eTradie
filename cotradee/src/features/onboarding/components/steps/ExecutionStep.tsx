import { useEffect, useState } from 'react';
import { useExecutionSettings, useUpdateExecutionSettings } from '@/features/execution/api/brokerAccount';
import { ChevronRight, Settings2, ShieldCheck } from 'lucide-react';

interface Props { onComplete: () => void; }

export function ExecutionStep({ onComplete }: Props) {
  const { data: settings } = useExecutionSettings();
  const updateSettings = useUpdateExecutionSettings();
  const [form, setForm] = useState({ 
    execution_mode: 'AUTO', 
    max_concurrent_trades: 3, 
    daily_loss_limit_pct: 3.0,
    weekly_drawdown_pct: 5.0
  });

  useEffect(() => {
    if (settings) {
      setForm({
        execution_mode: settings.execution_mode || 'AUTO',
        max_concurrent_trades: settings.max_concurrent_trades ?? 3,
        daily_loss_limit_pct: settings.daily_loss_limit_pct ?? 3.0,
        weekly_drawdown_pct: settings.weekly_drawdown_pct ?? 5.0
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
    <div className="w-full max-w-lg mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <Settings2 className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Risk & Execution</h2>
        <p className="mt-2 text-sm text-content-secondary leading-relaxed">
          Configure how the AI interacts with your broker account.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-surface-2 p-4 sm:p-6 space-y-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <span className="text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40 ml-1 sm:ml-0">Execution Mode</span>
          <div className="flex items-center bg-black/5 dark:bg-white/5 rounded-xl p-1 border border-black/10 dark:border-white/10 w-full sm:w-auto overflow-x-auto">
            {['AUTO', 'LIMIT', 'INSTANT'].map((mode) => (
              <button
                key={mode}
                onClick={() => setForm((f) => ({ ...f, execution_mode: mode }))}
                className={`flex-1 sm:flex-none px-4 py-2 text-[9px] font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${
                  form.execution_mode === mode
                    ? 'bg-black dark:bg-white text-white dark:text-black shadow-lg shadow-black/10 dark:shadow-white/10'
                    : 'text-black/40 dark:text-white/40 hover:text-black dark:hover:text-white'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
          <Field
            label="Max Concurrent Trades"
            type="number"
            value={form.max_concurrent_trades}
            onChange={(v) =>
              setForm((f) => ({ ...f, max_concurrent_trades: Number(v) }))
            }
          />
          <Field
            label="Daily Loss Limit %"
            type="number"
            step="0.1"
            value={form.daily_loss_limit_pct}
            onChange={(v) =>
              setForm((f) => ({ ...f, daily_loss_limit_pct: parseFloat(String(v)) }))
            }
          />
          <Field
            label="Weekly Drawdown %"
            type="number"
            step="0.1"
            value={form.weekly_drawdown_pct}
            onChange={(v) =>
              setForm((f) => ({ ...f, weekly_drawdown_pct: parseFloat(String(v)) }))
            }
          />
        </div>

        <button
          onClick={handleSave}
          disabled={updateSettings.isPending}
          className="w-full rounded-xl bg-black dark:bg-white p-3.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg shadow-black/10 dark:shadow-white/10 mt-6"
        >
          {updateSettings.isPending ? 'Saving...' : <>Save configuration <ChevronRight size={14} strokeWidth={3} /></>}
        </button>

        <div className="flex items-center justify-center gap-2 pt-2 text-[10px] text-content-muted font-semibold">
          <ShieldCheck size={14} />
          <span>These limits are enforced by the Execution Engine.</span>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  step,
  onChange,
}: {
  label: string;
  type: string;
  value: string | number;
  step?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 ml-1">{label}</label>
      <input
        type={type}
        value={value}
        step={step}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
      />
    </div>
  );
}
