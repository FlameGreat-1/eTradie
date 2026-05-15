import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
import {
  useExecutionSettings,
  useUpdateExecutionSettings,
} from '@/features/execution/api/brokerAccount';
import ProFeatureLock from '@/components/ui/ProFeatureLock';

export default function ExecutionSection() {
  const { data: settings } = useExecutionSettings();
  const updateSettings = useUpdateExecutionSettings();

  const [form, setForm] = useState({
    execution_mode: 'AUTO',
    max_concurrent_trades: 3,
    daily_loss_limit_pct: 3.0,
    weekly_drawdown_pct: 5.0,
  });

  useEffect(() => {
    if (settings) {
      setForm({
        execution_mode: settings.execution_mode || 'AUTO',
        max_concurrent_trades: settings.max_concurrent_trades ?? 3,
        daily_loss_limit_pct: settings.daily_loss_limit_pct ?? 3.0,
        weekly_drawdown_pct: settings.weekly_drawdown_pct ?? 5.0,
      });
    }
  }, [settings]);

  const handleSave = () => {
    updateSettings.mutate(form);
  };

  // The Execution section is a Pro-only surface end-to-end. The
  // ProFeatureLock wrapper renders the canonical locked message for
  // Free users (the spec verbatim) and the original form for Pro/admin.
  // 'replace' variant is intentional: the dimmed-children variant
  // would still show editable inputs which is misleading.
  return (
    <div className="space-y-10 max-w-lg">
      <div className="flex flex-col gap-0.5">
        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Automation</div>
        <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Execution Settings</h3>
      </div>
      <ProFeatureLock feature="execution" variant="overlay">
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">Execution Mode</span>
            <div className="flex items-center bg-black/5 dark:bg-white/5 rounded-xl p-1 border border-black/10 dark:border-white/10">
              {['AUTO', 'LIMIT', 'INSTANT'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setForm((f) => ({ ...f, execution_mode: mode }))}
                  className={`px-4 py-2 text-[9px] font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${
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

          <div className="grid grid-cols-2 gap-6">
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
              value={form.daily_loss_limit_pct}
              step="0.1"
              onChange={(v) =>
                setForm((f) => ({ ...f, daily_loss_limit_pct: parseFloat(String(v)) }))
              }
            />
            <Field
              label="Weekly Drawdown %"
              type="number"
              value={form.weekly_drawdown_pct}
              step="0.1"
              onChange={(v) =>
                setForm((f) => ({ ...f, weekly_drawdown_pct: parseFloat(String(v)) }))
              }
            />
          </div>

          <button
            onClick={handleSave}
            disabled={updateSettings.isPending}
            className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-8 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
          >
            <Save size={14} strokeWidth={3} /> {updateSettings.isPending ? 'Saving…' : 'Save Settings'}
          </button>
        </div>
      </ProFeatureLock>
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
