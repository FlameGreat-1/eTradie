import { useAnalysisDetail } from '../api/analysis';
import { X, TrendingUp, TrendingDown, AlertTriangle, Clock, Crosshair, ArrowLeftRight, ShieldOff, Flag, BadgeDollarSign } from 'lucide-react';

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
      <div className="max-h-[85vh] overflow-y-auto space-y-6 no-scrollbar">
        {/* Header */}
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl ${dirBg} ${dirColor} font-black text-xs uppercase tracking-wider`}>
              {isLong ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {direction}
            </div>
            <h2 className="text-xl font-black text-content tracking-tight">{data.pair}</h2>
          </div>
          <button onClick={onClose} className="w-10 h-10 flex items-center justify-center rounded-2xl hover:bg-surface-3 text-content-muted transition-all"><X size={20} /></button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricBadge label="Grade" value={data.setup_grade ?? raw.grade ?? raw.setup_grade ?? '-'} highlight />
          <MetricBadge label="Confidence" value={confDisplay} />
          <MetricBadge label="R:R Ratio" value={data.rr_ratio != null ? `${data.rr_ratio}:1` : raw.rr_ratio != null ? `${raw.rr_ratio}:1` : '-'} />
          <MetricBadge label="Confluence" value={confluenceScore != null ? `${confluenceScore}/10` : '-'} />
        </div>

        {/* Price Levels */}
        {(entryPrice || stopLoss || tp1) && (
          <section>
            <SectionTitle>Price Levels</SectionTitle>
            <div className="rounded-2xl border border-border bg-white dark:bg-black divide-y divide-border overflow-hidden">
              {entryPrice != null && (
                <PriceRow icon={<Crosshair size={14} className="text-brand" />} label="Entry Price" value={entryPrice} />
              )}
              {entryLow != null && entryHigh != null && (
                <PriceRow icon={<ArrowLeftRight size={14} className="text-brand/70" />} label="Entry Zone" value={`${entryLow} – ${entryHigh}`} />
              )}
              {stopLoss != null && (
                <PriceRow icon={<ShieldOff size={14} className="text-danger" />} label="Stop Loss" value={stopLoss} />
              )}
              {tp1 != null && <PriceRow icon={<Flag size={14} className="text-success" />} label={`TP1 ${tp1_pct ? `(${tp1_pct}%)` : ''}`} value={tp1} />}
              {tp2 != null && <PriceRow icon={<Flag size={14} className="text-success/80" />} label={`TP2 ${tp2_pct ? `(${tp2_pct}%)` : ''}`} value={tp2} />}
              {tp3 != null && <PriceRow icon={<Flag size={14} className="text-success/60" />} label={`TP3 ${tp3_pct ? `(${tp3_pct}%)` : ''}`} value={tp3} />}
              {takeProfit != null && !tp1 && (
                <PriceRow icon={<BadgeDollarSign size={14} className="text-success" />} label="Take Profit" value={takeProfit} />
              )}
            </div>
          </section>
        )}

        {/* AI Reasoning */}
        {reasoning && (
          <section>
            <SectionTitle>AI Reasoning</SectionTitle>
            <div className="rounded-2xl border border-border bg-white dark:bg-black p-5 text-[13px] font-medium text-content-secondary leading-relaxed whitespace-pre-wrap border-l-4 border-l-brand/50">
              {reasoning}
            </div>
          </section>
        )}

        {/* Rejection Rules */}
        {raw.rejection_rules?.length > 0 && (
          <section className="rounded-2xl border border-danger/30 bg-danger/5 p-4">
            <div className="flex items-center gap-2 text-[11px] font-black text-danger uppercase tracking-wider mb-2">
              <AlertTriangle size={14} /> Rejection Rules Triggered
            </div>
            {raw.rejection_rules.map((r: string, i: number) => (
              <div key={i} className="text-[11px] font-bold text-danger/80 ml-6 list-item">{r}</div>
            ))}
          </section>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between text-[11px] font-bold text-content-muted pt-4 border-t border-border mt-6">
          <div className="flex items-center gap-4">
            {(data.trading_style || raw.trading_style) && <span className="uppercase tracking-wider">{data.trading_style ?? raw.trading_style}</span>}
            {(data.session || raw.session) && <span className="uppercase tracking-wider">• {data.session ?? raw.session}</span>}
          </div>
          {data.created_at && (
            <span className="flex items-center gap-1.5 opacity-70">
              <Clock size={12} /> {new Date(data.created_at).toLocaleString()}
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
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-white dark:bg-black rounded-[2rem] border border-border p-8 shadow-2xl animate-fade-in">
        {children}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[11px] font-black text-content-muted uppercase tracking-widest mb-3 ml-1">{children}</h3>;
}

function MetricBadge({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-surface-2 p-4 text-center group hover:border-brand/50 transition-all">
      <span className="block text-[10px] font-black text-content-muted uppercase tracking-widest mb-1">{label}</span>
      <span className={`block text-lg font-black tracking-tight ${highlight ? 'text-brand' : 'text-content'}`}>{value}</span>
    </div>
  );
}

function PriceRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5 hover:bg-surface-3 transition-colors">
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-[11px] font-bold text-content-muted uppercase tracking-wider">{label}</span>
      </div>
      <span className="text-[13px] font-mono font-black text-content">{String(value)}</span>
    </div>
  );
}
