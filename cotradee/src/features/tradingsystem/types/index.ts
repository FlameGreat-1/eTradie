// Mirrors src/tradingsystem/models.go field-for-field. Keep in lock-
// step with the Go source of truth; any drift here is a typed bug
// the SPA build will catch before runtime.
//
// The gateway also exposes the closed-enum catalogue at
// GET /api/v1/trading-system/schema so the builder UI can render
// dropdowns from a runtime fetch (useful when adding a new enum
// without redeploying the SPA). The literal-union types below are
// the build-time guarantee; the runtime catalogue is the convenience
// for dynamic rendering.

export type TradingSystemStatus = 'none' | 'skipped' | 'active';

// Section 1 — Identity
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type AutomationLevel = 'manual' | 'semi_automated' | 'fully_automated';
export type RiskAppetite = 'conservative' | 'balanced' | 'aggressive';
export type TraderType = 'precision' | 'frequent';
export type DisciplineStyle = 'rule_based' | 'flexible_discretion';

export interface Identity {
  experience: ExperienceLevel;
  automation: AutomationLevel;
  risk_appetite: RiskAppetite;
  trader_type: TraderType;
  discipline: DisciplineStyle;
}

// Section 2 — Style
export type TradingStyle = 'scalping' | 'intraday' | 'swing' | 'positional';

// Section 3 — Sessions
export type Session = 'asian' | 'london' | 'new_york' | 'london_ny_overlap';
export interface SessionPreferences {
  preferred_sessions: Session[];
  avoid_low_liquidity: boolean;
  high_volatility_windows_only: boolean;
}

// Section 4 — Risk Personality
export type RiskModel = 'fixed' | 'adaptive';
export interface RiskPersonality {
  risk_model: RiskModel;
  fixed_risk_percent: number;
  max_daily_drawdown_percent: number;
  max_weekly_drawdown_percent: number;
  max_simultaneous_trades: number;
  max_correlated_exposure: number;
  partial_take_profits: boolean;
  break_even_management: boolean;
  trailing_stop_enabled: boolean;
}

// Section 5 — Confirmation
export type ConfirmationStrictness = 'aggressive' | 'balanced' | 'strict';

// Section 6 — Structural
export type StructuralFramework = 'smc' | 'snd' | 'wyckoff' | 'liquidity';
export type EmphasisLevel = 'low' | 'medium' | 'high';
export interface StructuralPreferences {
  frameworks: StructuralFramework[];
  use_fvg: boolean;
  use_order_blocks: boolean;
  use_choch_bms: boolean;
  use_idm: boolean;
  structure_emphasis: EmphasisLevel;
}

// Section 7 — Entry
export type EntryExecutionMode = 'limit_only' | 'market_allowed' | 'either_allowed';
export interface EntryPreferences {
  execution_mode: EntryExecutionMode;
  require_confirmation_candle: boolean;
  require_retest: boolean;
  require_liquidity_sweep: boolean;
  require_mtf_alignment: boolean;
}

// Section 8 — Trade Filtering
export interface TradeFiltering {
  avoid_counter_trend: boolean;
  avoid_news_volatility: boolean;
  minimum_rr: number;
  avoid_ranging_markets: boolean;
  avoid_overnight_holds: boolean;
  avoid_friday_trades: boolean;
  avoid_session_transitions: boolean;
}

// Section 9 — Psychological Constraints
export interface PsychologicalConstraints {
  max_losses_before_cooldown: number;
  cooldown_after_loss_streak: boolean;
  daily_lockout_after_target: boolean;
  revenge_trading_protection: boolean;
  overtrading_protection: boolean;
  emotional_volatility_sensitivity: EmphasisLevel;
}

// Section 10 — Confluence (weights 0..3)
export interface ConfluenceWeights {
  macro_alignment: number;
  dxy: number;
  cot: number;
  htf_alignment: number;
  wyckoff: number;
  volume_liquidity: number;
  session_timing: number;
}

// Section 11 — Automation
export type ExecutionAutomationMode =
  | 'alert_only'
  | 'manual_approval'
  | 'semi_automatic'
  | 'fully_automatic';
export interface AutomationPreferences {
  mode: ExecutionAutomationMode;
  require_final_confirmation: boolean;
  allow_unattended_execution: boolean;
}

// Section 12 — Assets
export type AssetClass =
  | 'forex'
  | 'indices'
  | 'gold'
  | 'crypto'
  | 'volatility_indices';
export interface AssetPreferences {
  asset_classes: AssetClass[];
  preferred_pairs: string[];
  avoid_highly_volatile: boolean;
  avoid_correlated_instruments: boolean;
}

// Section 13 — Goal
export type GoalOrientation =
  | 'capital_preservation'
  | 'consistency'
  | 'aggressive_growth'
  | 'low_stress'
  | 'high_probability_only'
  | 'fewer_high_quality';

// Section 14 — Management
export type PartialTPStyle = 'disabled' | 'aggressive' | 'balanced' | 'let_run';
export type TrailingStopBehaviour =
  | 'disabled'
  | 'structure_based'
  | 'atr_based'
  | 'fixed_pips';
export type BreakEvenTrigger =
  | 'disabled'
  | 'at_tp1'
  | 'at_1rr'
  | 'at_midpoint';
export interface TradeManagement {
  partial_tp_style: PartialTPStyle;
  trailing_stop: TrailingStopBehaviour;
  break_even_trigger: BreakEvenTrigger;
  scale_in_enabled: boolean;
  scale_out_enabled: boolean;
  hold_runners: boolean;
  close_before_news: boolean;
}

// The full profile. schema_version is set by the backend on save.
export interface TradingSystemProfile {
  schema_version: number;
  identity: Identity;
  style: TradingStyle;
  sessions: SessionPreferences;
  risk: RiskPersonality;
  confirmation: ConfirmationStrictness;
  structural: StructuralPreferences;
  entry: EntryPreferences;
  filtering: TradeFiltering;
  psychology: PsychologicalConstraints;
  confluence: ConfluenceWeights;
  automation: AutomationPreferences;
  assets: AssetPreferences;
  goal: GoalOrientation;
  management: TradeManagement;
}

// Wire shape returned by GET /api/v1/trading-system.
export interface TradingSystemRecord {
  status: TradingSystemStatus;
  version: number;
  profile: TradingSystemProfile | null;
  has_profile: boolean;
  created_at?: string;
  updated_at?: string;
}

// Wire shape returned by GET /api/v1/trading-system/status.
export interface TradingSystemStatusView {
  status: TradingSystemStatus;
  version: number;
  has_profile: boolean;
  updated_at?: string;
}

// Wire shape returned by GET /api/v1/trading-system/schema.
export interface TradingSystemSchemaCatalogue {
  schema_version: number;
  identity: {
    experience: ExperienceLevel[];
    automation: AutomationLevel[];
    risk_appetite: RiskAppetite[];
    trader_type: TraderType[];
    discipline: DisciplineStyle[];
  };
  style: TradingStyle[];
  sessions: Session[];
  risk_model: RiskModel[];
  confirmation: ConfirmationStrictness[];
  frameworks: StructuralFramework[];
  entry_mode: EntryExecutionMode[];
  automation_modes: ExecutionAutomationMode[];
  asset_class: AssetClass[];
  goal: GoalOrientation[];
  partial_tp: PartialTPStyle[];
  trailing_stop: TrailingStopBehaviour[];
  break_even: BreakEvenTrigger[];
  emphasis: EmphasisLevel[];
  limits: Record<
    string,
    { min: number; max: number }
  >;
}

// Thrown by saveTradingSystem on HTTP 422. Carries per-field error
// messages so the builder UI can render them inline next to each
// section.
export class TradingSystemValidationError extends Error {
  public readonly fields: Record<string, string>;
  constructor(message: string, fields: Record<string, string>) {
    super(message);
    this.name = 'TradingSystemValidationError';
    this.fields = fields;
  }
}
