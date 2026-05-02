import { useExecutionSettings, useUpdateExecutionSettings } from '@/features/execution/api/brokerAccount';
import { useState, useEffect } from 'react';
import { Save } from 'lucide-react';

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

  return (
    <div className="space-y-6 max-w-lg">
      <h3 className="text-sm font-semibold text-content">Execution Settings</h3>

      <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-4">
        {/* Execution Mode Segmented Control */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-content">Execution Mode</span>
          <div className="flex items-center bg-surface-2 rounded-lg p-0.5 border border-border">
            {['AUTO', 'LIMIT', 'INSTANT'].map((mode) => (
              <button
                key={mode}
                onClick={() => setForm((f) => ({ ...f, execution_mode: mode }))}
                className={`px-3 py-1 text-[10px] font-medium rounded-md transition-colors ${
                  form.execution_mode === mode
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-content-muted hover:text-content hover:bg-surface-3'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Max Concurrent Trades" type="number" value={form.max_concurrent_trades}
            onChange={(v) => setForm((f) => ({ ...f, max_concurrent_trades: Number(v) }))} />
          <Field label="Daily Loss Limit %" type="number" value={form.daily_loss_limit_pct} step="0.1"
            onChange={(v) => setForm((f) => ({ ...f, daily_loss_limit_pct: parseFloat(String(v)) }))} />
          <Field label="Weekly Drawdown %" type="number" value={form.weekly_drawdown_pct} step="0.1"
            onChange={(v) => setForm((f) => ({ ...f, weekly_drawdown_pct: parseFloat(String(v)) }))} />
        </div>

        <button onClick={handleSave} disabled={updateSettings.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white
                     hover:bg-brand-dark disabled:opacity-50 transition-colors">
          <Save size={12} /> {updateSettings.isPending ? 'Saving…' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}

function Field({ label, type, value, step, onChange }: {
  label: string; type: string; value: string | number; step?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-content-muted">{label}</label>
      <input type={type} value={value} step={step}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-content
                   focus:border-brand focus:outline-none transition-colors" />
    </div>
  );
}
