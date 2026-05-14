import { memo } from 'react';
import type { TradingSystemProfile } from '../../types';
import { StepShell } from '../StepShell';

interface Props {
  profile: TradingSystemProfile;
  onEditStep: (stepIndex: number) => void;
  stepNumber: number;
  totalSteps: number;
  hideHeader?: boolean;
}

/**
 * Final read-only review. The user sees every section condensed into
 * a short label list, with an Edit button per section that jumps the
 * stepper back to the relevant step.
 */
function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-xs text-content-muted">{label}</span>
      <span className="text-xs font-medium text-content text-right">{value}</span>
    </div>
  );
}

function Section({
  title,
  onEdit,
  children,
}: {
  title: string;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between mb-1.5">
        <h3 className="text-sm font-semibold text-content">{title}</h3>
        <button
          type="button"
          onClick={onEdit}
          className="text-xs font-medium text-brand hover:underline focus-ring rounded"
        >
          Edit
        </button>
      </div>
      <div className="divide-y divide-border/60">{children}</div>
    </div>
  );
}

function yesNo(b: boolean): string {
  return b ? 'Yes' : 'No';
}

function joinList(items: string[]): string {
  if (!items || items.length === 0) return '—';
  return items.join(', ');
}

function ReviewStepInner({ profile, onEditStep, stepNumber, totalSteps, hideHeader }: Props) {
  const { identity, sessions, risk, structural, entry, filtering, psychology, confluence, automation, assets, management } = profile;
  
  const content = (
    <div className="space-y-4">
      <Section title="1. Identity" onEdit={() => onEditStep(0)}>
        <ReviewRow label="Experience" value={identity.experience} />
        <ReviewRow label="Execution" value={identity.automation} />
        <ReviewRow label="Risk appetite" value={identity.risk_appetite} />
        <ReviewRow label="Trader type" value={identity.trader_type} />
        <ReviewRow label="Discipline" value={identity.discipline} />
      </Section>

      <Section title="2. Style" onEdit={() => onEditStep(1)}>
        <ReviewRow label="Style" value={profile.style} />
      </Section>

      <Section title="3. Sessions" onEdit={() => onEditStep(2)}>
        <ReviewRow label="Preferred" value={joinList(sessions.preferred_sessions)} />
        <ReviewRow label="Avoid low liquidity" value={yesNo(sessions.avoid_low_liquidity)} />
        <ReviewRow label="High-volatility windows only" value={yesNo(sessions.high_volatility_windows_only)} />
      </Section>

      <Section title="4. Risk Personality" onEdit={() => onEditStep(3)}>
        <ReviewRow label="Risk model" value={risk.risk_model} />
        <ReviewRow label="Per-trade risk" value={`${risk.fixed_risk_percent}%`} />
        <ReviewRow label="Max daily drawdown" value={`${risk.max_daily_drawdown_percent}%`} />
        <ReviewRow label="Max weekly drawdown" value={`${risk.max_weekly_drawdown_percent}%`} />
        <ReviewRow label="Max simultaneous" value={String(risk.max_simultaneous_trades)} />
        <ReviewRow label="Max correlated" value={String(risk.max_correlated_exposure)} />
        <ReviewRow label="Partial TPs" value={yesNo(risk.partial_take_profits)} />
        <ReviewRow label="Break-even mgmt" value={yesNo(risk.break_even_management)} />
        <ReviewRow label="Trailing stop" value={yesNo(risk.trailing_stop_enabled)} />
      </Section>

      <Section title="5. Confirmation" onEdit={() => onEditStep(4)}>
        <ReviewRow label="Strictness" value={profile.confirmation} />
      </Section>

      <Section title="6. Structural" onEdit={() => onEditStep(5)}>
        <ReviewRow label="Frameworks" value={joinList(structural.frameworks)} />
        <ReviewRow label="FVG" value={yesNo(structural.use_fvg)} />
        <ReviewRow label="Order Blocks" value={yesNo(structural.use_order_blocks)} />
        <ReviewRow label="CHoCH / BMS" value={yesNo(structural.use_choch_bms)} />
        <ReviewRow label="IDM" value={yesNo(structural.use_idm)} />
        <ReviewRow label="Emphasis" value={structural.structure_emphasis} />
      </Section>

      <Section title="7. Entry" onEdit={() => onEditStep(6)}>
        <ReviewRow label="Execution mode" value={entry.execution_mode} />
        <ReviewRow label="Confirmation candle" value={yesNo(entry.require_confirmation_candle)} />
        <ReviewRow label="Retest" value={yesNo(entry.require_retest)} />
        <ReviewRow label="Liquidity sweep" value={yesNo(entry.require_liquidity_sweep)} />
        <ReviewRow label="MTF alignment" value={yesNo(entry.require_mtf_alignment)} />
      </Section>

      <Section title="8. Trade Filtering" onEdit={() => onEditStep(7)}>
        <ReviewRow label="Minimum RR" value={`${filtering.minimum_rr}:1`} />
        <ReviewRow label="Avoid counter-trend" value={yesNo(filtering.avoid_counter_trend)} />
        <ReviewRow label="Avoid news" value={yesNo(filtering.avoid_news_volatility)} />
        <ReviewRow label="Avoid ranging" value={yesNo(filtering.avoid_ranging_markets)} />
        <ReviewRow label="Avoid overnight" value={yesNo(filtering.avoid_overnight_holds)} />
        <ReviewRow label="Avoid Friday" value={yesNo(filtering.avoid_friday_trades)} />
        <ReviewRow label="Avoid session transitions" value={yesNo(filtering.avoid_session_transitions)} />
      </Section>

      <Section title="9. Psychology" onEdit={() => onEditStep(8)}>
        <ReviewRow label="Max losses" value={String(psychology.max_losses_before_cooldown)} />
        <ReviewRow label="Loss-streak cooldown" value={yesNo(psychology.cooldown_after_loss_streak)} />
        <ReviewRow label="Daily lockout" value={yesNo(psychology.daily_lockout_after_target)} />
        <ReviewRow label="Revenge protection" value={yesNo(psychology.revenge_trading_protection)} />
        <ReviewRow label="Overtrading protection" value={yesNo(psychology.overtrading_protection)} />
        <ReviewRow label="Volatility sensitivity" value={psychology.emotional_volatility_sensitivity} />
      </Section>

      <Section title="10. Confluence Weights" onEdit={() => onEditStep(9)}>
        <ReviewRow label="Macro" value={String(confluence.macro_alignment)} />
        <ReviewRow label="DXY" value={String(confluence.dxy)} />
        <ReviewRow label="COT" value={String(confluence.cot)} />
        <ReviewRow label="HTF" value={String(confluence.htf_alignment)} />
        <ReviewRow label="Wyckoff" value={String(confluence.wyckoff)} />
        <ReviewRow label="Volume / liquidity" value={String(confluence.volume_liquidity)} />
        <ReviewRow label="Session timing" value={String(confluence.session_timing)} />
      </Section>

      <Section title="11. Automation" onEdit={() => onEditStep(10)}>
        <ReviewRow label="Mode" value={automation.mode} />
        <ReviewRow label="Final confirmation" value={yesNo(automation.require_final_confirmation)} />
        <ReviewRow label="Unattended execution" value={yesNo(automation.allow_unattended_execution)} />
      </Section>

      <Section title="12. Assets" onEdit={() => onEditStep(11)}>
        <ReviewRow label="Classes" value={joinList(assets.asset_classes)} />
        <ReviewRow label="Preferred pairs" value={joinList(assets.preferred_pairs)} />
        <ReviewRow label="Avoid high volatility" value={yesNo(assets.avoid_highly_volatile)} />
        <ReviewRow label="Avoid correlated" value={yesNo(assets.avoid_correlated_instruments)} />
      </Section>

      <Section title="13. Goal" onEdit={() => onEditStep(12)}>
        <ReviewRow label="Orientation" value={profile.goal} />
      </Section>

      <Section title="14. Trade Management" onEdit={() => onEditStep(13)}>
        <ReviewRow label="Partial TP style" value={management.partial_tp_style} />
        <ReviewRow label="Trailing stop" value={management.trailing_stop} />
        <ReviewRow label="Break-even trigger" value={management.break_even_trigger} />
        <ReviewRow label="Scale-in" value={yesNo(management.scale_in_enabled)} />
        <ReviewRow label="Scale-out" value={yesNo(management.scale_out_enabled)} />
        <ReviewRow label="Hold runners" value={yesNo(management.hold_runners)} />
        <ReviewRow label="Close before news" value={yesNo(management.close_before_news)} />
      </Section>
    </div>
  );

  if (hideHeader) {
    return content;
  }

  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Review & Confirm"
      description="Final check. Click any section to edit. When you save, Exoper starts using these preferences immediately."
    >
      {content}
    </StepShell>
  );
}

export const ReviewStep = memo(ReviewStepInner);
