import { useAnalysisDetail } from '../api/analysis';
import { X, TrendingUp, TrendingDown, AlertTriangle, Clock, Shield, Target } from 'lucide-react';

interface Props {
  analysisId: string;
  onClose: () => void;
}

export default function AnalysisDetailModal({ analysisId, onClose }: Props) {
  const { data, isLoading, error } = useAnalysisDetail(analysisId);

  if (isLoading) {
    return <Overlay onClose={onClose}><div className="p-12 text-center text-content-muted">Loading analysis…</div></Overlay>;
  }

  if (error || !data) {
    return <Overlay onClose={onClose}><div className="p-12 text-center text-danger">Failed to load analysis</div></Overlay>;
  }

  // Use raw_output as primary source for rich data
  const raw = data.raw_output ?? {};
  const direction = data.direction ?? raw.direction ?? '-';
  const isLong = direction === 'LONG' || direction === 'BUY';
  const dirColor = isLong ? 'text-success' : 'text-danger';
  const dirBg = isLong ? 'bg-success/10' : 'bg-danger/10';

  let confDisplay = '-';
  const confValue = raw.confidence ?? data.confidence;
  if (typeof confValue === 'number' && !isNaN(confValue)) {
    confDisplay = `${Math.round(confValue * 100)}%`;
  } else if (typeof confValue === 'string') {
    confDisplay = confValue;
  }

  const reasoning = raw.explainable_reasoning ?? raw.reasoning ?? data.display?.reasoning;
  const entryPrice = raw.entry_price ?? raw.entry_zone?.low; 
  const entryLow = raw.entry_zone_low ?? raw.entry_zone?.low;
  const entryHigh = raw.entry_zone_high ?? raw.entry_zone?.high;

  // Handle nested stop loss object
  const stopLoss = typeof raw.stop_loss === 'object' && raw.stop_loss !== null 
    ? raw.stop_loss.price 
    : raw.stop_loss;

  // Handle take profit array
  const tp1 = raw.tp1_price ?? (raw.take_profits?.[0]?.level);
  const tp2 = raw.tp2_price ?? (raw.take_profits?.[1]?.level);
  const tp3 = raw.tp3_price ?? (raw.take_profits?.[2]?.level);
  const tp1_pct = raw.tp1_pct ?? raw.take_profits?.[0]?.size_pct;
  const tp2_pct = raw.tp2_pct ?? raw.take_profits?.[1]?.size_pct;
  const tp3_pct = raw.tp3_pct ?? raw.take_profits?.[2]?.size_pct;
  const takeProfit = raw.take_profit;

  // Confluence Score object
  const confluenceScore = typeof raw.confluence_score === 'object' && raw.confluence_score !== null
    ? raw.confluence_score.score
    : raw.confluence_score ?? data.confluence_score;

  return (
    <Overlay onClose={onClose}>
      <div className="max-h-[85vh] overflow-y-auto space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${dirBg} ${dirColor} font-bold text-sm`}>
              {isLong ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              {direction}
            </div>
            <h2 className="text-lg font-bold text-content">{data.pair}</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-surface-2 text-content-muted"><X size={18} /></button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricBadge label="Grade" value={data.setup_grade ?? raw.grade ?? raw.setup_grade ?? '-'} highlight />
          <MetricBadge label="Confidence" value={confDisplay} />
          <MetricBadge label="R:R Ratio" value={data.rr_ratio != null ? `${data.rr_ratio}:1` : raw.rr_ratio != null ? `${raw.rr_ratio}:1` : '-'} />
          <MetricBadge label="Confluence" value={confluenceScore != null ? `${confluenceScore}/10` : '-'} />
        </div>

        {/* Price Levels */}
        {(entryPrice || stopLoss || tp1) && (
          <section>
            <SectionTitle>Price Levels</SectionTitle>
            <div className="rounded-lg border border-border bg-surface-2 divide-y divide-border">
              {entryPrice != null && (
                <PriceRow icon={<Target size={13} className="text-brand" />} label="Entry Price" value={entryPrice} />
              )}
              {entryLow != null && entryHigh != null && (
                <PriceRow icon={<Target size={13} className="text-brand/60" />} label="Entry Zone" value={`${entryLow} – ${entryHigh}`} />
              )}
              {stopLoss != null && (
                <PriceRow icon={<Shield size={13} className="text-danger" />} label="Stop Loss" value={stopLoss} />
              )}
              {tp1 != null && <PriceRow icon={<Target size={13} className="text-success" />} label={`TP1 ${tp1_pct ? `(${tp1_pct}%)` : ''}`} value={tp1} />}
              {tp2 != null && <PriceRow icon={<Target size={13} className="text-success/80" />} label={`TP2 ${tp2_pct ? `(${tp2_pct}%)` : ''}`} value={tp2} />}
              {tp3 != null && <PriceRow icon={<Target size={13} className="text-success/60" />} label={`TP3 ${tp3_pct ? `(${tp3_pct}%)` : ''}`} value={tp3} />}
              {takeProfit != null && !tp1 && (
                <PriceRow icon={<Target size={13} className="text-success" />} label="Take Profit" value={takeProfit} />
              )}
            </div>
          </section>
        )}

        {/* AI Reasoning */}
        {reasoning && (
          <section>
            <SectionTitle>AI Reasoning</SectionTitle>
            <div className="rounded-lg border border-border bg-surface-2 p-4 text-xs text-content leading-relaxed whitespace-pre-wrap">
              {reasoning}
            </div>
          </section>
        )}

        {/* Rejection Rules */}
        {raw.rejection_rules?.length > 0 && (
          <section className="rounded-lg border border-warning/30 bg-warning/5 p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-warning mb-1">
              <AlertTriangle size={12} /> Rejection Rules Triggered
            </div>
            {raw.rejection_rules.map((r: string, i: number) => (
              <div key={i} className="text-xs text-warning/80 ml-4">• {r}</div>
            ))}
          </section>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between text-[10px] text-content-muted pt-2 border-t border-border mt-4">
          <div className="flex items-center gap-3">
            {(data.trading_style || raw.trading_style) && <span>{data.trading_style ?? raw.trading_style}</span>}
            {(data.session || raw.session) && <span>• {data.session ?? raw.session}</span>}
            {raw.execution_mode && <span>• {raw.execution_mode}</span>}
            {raw.risk_percentage != null && <span>• Risk: {raw.risk_percentage}%</span>}
          </div>
          {data.created_at && (
            <span className="flex items-center gap-1">
              <Clock size={10} /> {new Date(data.created_at).toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </Overlay>
  );
}

/* ── Sub-components ──────────────────────────────── */

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl mx-4 rounded-2xl border border-border bg-surface-0 p-6 shadow-2xl animate-fade-in">
        {children}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-xs font-semibold text-content-muted uppercase tracking-wide mb-2">{children}</h3>;
}

function MetricBadge({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3 text-center">
      <span className="block text-[10px] text-content-muted uppercase tracking-wide">{label}</span>
      <span className={`block text-base font-bold mt-0.5 ${highlight ? 'text-brand' : 'text-content'}`}>{value}</span>
    </div>
  );
}

function PriceRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between px-3 py-2">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs text-content-muted">{label}</span>
      </div>
      <span className="text-xs font-mono font-semibold text-content">{String(value)}</span>
    </div>
  );
}
