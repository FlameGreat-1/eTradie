import { useExecutionSettings, useUpdateExecutionSettings } from '@/features/execution/api/brokerAccount';
import { useState, useEffect } from 'react';
import { Save } from 'lucide-react';

export default function ExecutionSection() {
  const { data: settings } = useExecutionSettings();
  const updateSettings = useUpdateExecutionSettings();

  const [form, setForm] = useState({
    enabled: false,
    max_positions: 10,
    max_daily_trades: 20,
    max_lot_size: 1.0,
    risk_percent: 1.0,
    allowed_symbols: [] as string[],
  });

  useEffect(() => {
    if (settings) {
      setForm({
        enabled: settings.enabled ?? false,
        max_positions: settings.max_positions ?? 10,
        max_daily_trades: settings.max_daily_trades ?? 20,
        max_lot_size: settings.max_lot_size ?? 1.0,
        risk_percent: settings.risk_percent ?? 1.0,
        allowed_symbols: settings.allowed_symbols ?? [],
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
        {/* Enable toggle */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-content">Execution Enabled</span>
          <button
            onClick={() => setForm((f) => ({ ...f, enabled: !f.enabled }))}
            className={`w-10 h-5 rounded-full transition-colors relative ${form.enabled ? 'bg-brand' : 'bg-border'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${form.enabled ? 'left-5' : 'left-0.5'}`} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Max Open Positions" type="number" value={form.max_positions}
            onChange={(v) => setForm((f) => ({ ...f, max_positions: Number(v) }))} />
          <Field label="Max Daily Trades" type="number" value={form.max_daily_trades}
            onChange={(v) => setForm((f) => ({ ...f, max_daily_trades: Number(v) }))} />
          <Field label="Max Lot Size" type="number" value={form.max_lot_size} step="0.01"
            onChange={(v) => setForm((f) => ({ ...f, max_lot_size: parseFloat(String(v)) }))} />
          <Field label="Risk %" type="number" value={form.risk_percent} step="0.1"
            onChange={(v) => setForm((f) => ({ ...f, risk_percent: parseFloat(String(v)) }))} />
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
