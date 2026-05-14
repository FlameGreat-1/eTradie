// Package tradingsystem implements the user-specific Trading Operating
// System: a structured, typed personalization layer that conditions LLM
// reasoning during analysis WITHOUT overriding the institutional RAG
// rulebook. See PRACTICE.md for the architectural rationale.
//
// Authority model (must remain true):
//
//   Layer 1 — Institutional RAG (global, never overridden)
//   Layer 2 — User Trading System (this package: preference weighting,
//             behavioural conditioning, soft constraints)
//   Layer 3 — Live market context (TA + Macro)
//
// The schema below maps 1:1 to PRACTICE.md Critical Session 1 sections
// 1 through 14. Every preference is a closed enum or a numeric value
// inside a validated range; no free-form text is accepted from the
// user. This keeps the downstream context builder in the Python engine
// deterministic and prevents prompt injection through the profile.
package tradingsystem

import (
	"time"
)

// Status is the lifecycle state of a user's trading system.
//
//   StatusNone    — the user has never engaged with onboarding; the
//                   platform applies the default institutional profile.
//   StatusSkipped — the user explicitly skipped the builder; treated
//                   the same as StatusNone for retrieval purposes but
//                   distinguished in the dashboard so we can offer a
//                   gentle prompt to complete it later.
//   StatusActive  — the user built (or regenerated) a profile and it
//                   should be injected into every analysis context.
type Status string

const (
	StatusNone    Status = "none"
	StatusSkipped Status = "skipped"
	StatusActive  Status = "active"
)

// IsValid reports whether the value is one of the recognised states.
func (s Status) IsValid() bool {
	switch s {
	case StatusNone, StatusSkipped, StatusActive:
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Section 1 — Trading Identity
// ---------------------------------------------------------------------------

type ExperienceLevel string

const (
	ExperienceBeginner     ExperienceLevel = "beginner"
	ExperienceIntermediate ExperienceLevel = "intermediate"
	ExperienceAdvanced     ExperienceLevel = "advanced"
)

type AutomationLevel string

const (
	AutomationManual         AutomationLevel = "manual"
	AutomationSemiAutomated  AutomationLevel = "semi_automated"
	AutomationFullyAutomated AutomationLevel = "fully_automated"
)

type RiskAppetite string

const (
	RiskAppetiteConservative RiskAppetite = "conservative"
	RiskAppetiteBalanced     RiskAppetite = "balanced"
	RiskAppetiteAggressive   RiskAppetite = "aggressive"
)

type TraderType string

const (
	TraderTypePrecision TraderType = "precision"
	TraderTypeFrequent  TraderType = "frequent"
)

type DisciplineStyle string

const (
	DisciplineRuleBased          DisciplineStyle = "rule_based"
	DisciplineFlexibleDiscretion DisciplineStyle = "flexible_discretion"
)

// Identity captures Section 1 of the PRACTICE.md questionnaire.
type Identity struct {
	Experience   ExperienceLevel `json:"experience"`
	Automation   AutomationLevel `json:"automation"`
	RiskAppetite RiskAppetite    `json:"risk_appetite"`
	TraderType   TraderType      `json:"trader_type"`
	Discipline   DisciplineStyle `json:"discipline"`
}

// ---------------------------------------------------------------------------
// Section 2 — Trading Style
// ---------------------------------------------------------------------------

type TradingStyle string

const (
	StyleScalping   TradingStyle = "scalping"
	StyleIntraday   TradingStyle = "intraday"
	StyleSwing      TradingStyle = "swing"
	StylePositional TradingStyle = "positional"
)

// ---------------------------------------------------------------------------
// Section 3 — Session Preferences
// ---------------------------------------------------------------------------

type Session string

const (
	SessionAsian           Session = "asian"
	SessionLondon          Session = "london"
	SessionNewYork         Session = "new_york"
	SessionLondonNYOverlap Session = "london_ny_overlap"
)

type SessionPreferences struct {
	PreferredSessions         []Session `json:"preferred_sessions"`
	AvoidLowLiquidity         bool      `json:"avoid_low_liquidity"`
	HighVolatilityWindowsOnly bool      `json:"high_volatility_windows_only"`
}

// ---------------------------------------------------------------------------
// Section 4 — Risk Personality
// ---------------------------------------------------------------------------

type RiskModel string

const (
	RiskModelFixed    RiskModel = "fixed"
	RiskModelAdaptive RiskModel = "adaptive"
)

type RiskPersonality struct {
	RiskModel                RiskModel `json:"risk_model"`
	FixedRiskPercent         float64   `json:"fixed_risk_percent"`          // 0.1 .. 3.0
	MaxDailyDrawdownPercent  float64   `json:"max_daily_drawdown_percent"`  // 1.0 .. 10.0
	MaxWeeklyDrawdownPercent float64   `json:"max_weekly_drawdown_percent"` // 2.0 .. 20.0
	MaxSimultaneousTrades    int       `json:"max_simultaneous_trades"`     // 1 .. 10
	MaxCorrelatedExposure    int       `json:"max_correlated_exposure"`     // 1 .. 5
	PartialTakeProfits       bool      `json:"partial_take_profits"`
	BreakEvenManagement      bool      `json:"break_even_management"`
	TrailingStopEnabled      bool      `json:"trailing_stop_enabled"`
}

// ---------------------------------------------------------------------------
// Section 5 — Confirmation Strictness
// ---------------------------------------------------------------------------

type ConfirmationStrictness string

const (
	ConfirmationAggressive ConfirmationStrictness = "aggressive"
	ConfirmationBalanced   ConfirmationStrictness = "balanced"
	ConfirmationStrict     ConfirmationStrictness = "strict"
)

// ---------------------------------------------------------------------------
// Section 6 — Structural Preferences
// ---------------------------------------------------------------------------

type StructuralFramework string

const (
	FrameworkSMC       StructuralFramework = "smc"
	FrameworkSnD       StructuralFramework = "snd"
	FrameworkWyckoff   StructuralFramework = "wyckoff"
	FrameworkLiquidity StructuralFramework = "liquidity"
)

type StructuralPreferences struct {
	Frameworks        []StructuralFramework `json:"frameworks"` // 1 or more
	UseFVG            bool                  `json:"use_fvg"`
	UseOrderBlocks    bool                  `json:"use_order_blocks"`
	UseCHoCHBMS       bool                  `json:"use_choch_bms"`
	UseIDM            bool                  `json:"use_idm"`
	StructureEmphasis string                `json:"structure_emphasis"` // low|medium|high
}

// ---------------------------------------------------------------------------
// Section 7 — Entry Preferences
// ---------------------------------------------------------------------------

type EntryExecutionMode string

const (
	EntryLimitOnly     EntryExecutionMode = "limit_only"
	EntryMarketAllowed EntryExecutionMode = "market_allowed"
	EntryEitherAllowed EntryExecutionMode = "either_allowed"
)

type EntryPreferences struct {
	ExecutionMode             EntryExecutionMode `json:"execution_mode"`
	RequireConfirmationCandle bool               `json:"require_confirmation_candle"`
	RequireRetest             bool               `json:"require_retest"`
	RequireLiquiditySweep     bool               `json:"require_liquidity_sweep"`
	RequireMTFAlignment       bool               `json:"require_mtf_alignment"`
}

// ---------------------------------------------------------------------------
// Section 8 — Trade Filtering
// ---------------------------------------------------------------------------

type TradeFiltering struct {
	AvoidCounterTrend       bool    `json:"avoid_counter_trend"`
	AvoidNewsVolatility     bool    `json:"avoid_news_volatility"`
	MinimumRR               float64 `json:"minimum_rr"` // 1.0 .. 10.0
	AvoidRangingMarkets     bool    `json:"avoid_ranging_markets"`
	AvoidOvernightHolds     bool    `json:"avoid_overnight_holds"`
	AvoidFridayTrades       bool    `json:"avoid_friday_trades"`
	AvoidSessionTransitions bool    `json:"avoid_session_transitions"`
}

// ---------------------------------------------------------------------------
// Section 9 — Psychological Constraints
// ---------------------------------------------------------------------------

type PsychologicalConstraints struct {
	MaxLossesBeforeCooldown        int    `json:"max_losses_before_cooldown"` // 0 .. 10
	CooldownAfterLossStreak        bool   `json:"cooldown_after_loss_streak"`
	DailyLockoutAfterTarget        bool   `json:"daily_lockout_after_target"`
	RevengeTradingProtection       bool   `json:"revenge_trading_protection"`
	OvertradingProtection          bool   `json:"overtrading_protection"`
	EmotionalVolatilitySensitivity string `json:"emotional_volatility_sensitivity"` // low|medium|high
}

// ---------------------------------------------------------------------------
// Section 10 — Confluence Preferences (weights 0..3)
// ---------------------------------------------------------------------------

type ConfluenceWeights struct {
	MacroAlignment  int `json:"macro_alignment"`
	DXY             int `json:"dxy"`
	COT             int `json:"cot"`
	HTFAlignment    int `json:"htf_alignment"`
	Wyckoff         int `json:"wyckoff"`
	VolumeLiquidity int `json:"volume_liquidity"`
	SessionTiming   int `json:"session_timing"`
}

// ---------------------------------------------------------------------------
// Section 11 — Automation
// ---------------------------------------------------------------------------

type ExecutionAutomationMode string

const (
	AutoAlertOnly      ExecutionAutomationMode = "alert_only"
	AutoManualApproval ExecutionAutomationMode = "manual_approval"
	AutoSemiAutomatic  ExecutionAutomationMode = "semi_automatic"
	AutoFullyAutomatic ExecutionAutomationMode = "fully_automatic"
)

type AutomationPreferences struct {
	Mode                     ExecutionAutomationMode `json:"mode"`
	RequireFinalConfirmation bool                    `json:"require_final_confirmation"`
	AllowUnattendedExecution bool                    `json:"allow_unattended_execution"`
}

// ---------------------------------------------------------------------------
// Section 12 — Assets
// ---------------------------------------------------------------------------

type AssetClass string

const (
	AssetForex             AssetClass = "forex"
	AssetIndices           AssetClass = "indices"
	AssetGold              AssetClass = "gold"
	AssetCrypto            AssetClass = "crypto"
	AssetVolatilityIndices AssetClass = "volatility_indices"
)

type AssetPreferences struct {
	AssetClasses               []AssetClass `json:"asset_classes"`   // 1+
	PreferredPairs             []string     `json:"preferred_pairs"` // optional, normalised upper-case
	AvoidHighlyVolatile        bool         `json:"avoid_highly_volatile"`
	AvoidCorrelatedInstruments bool         `json:"avoid_correlated_instruments"`
}

// ---------------------------------------------------------------------------
// Section 13 — Goal Orientation
// ---------------------------------------------------------------------------

type GoalOrientation string

const (
	GoalCapitalPreservation GoalOrientation = "capital_preservation"
	GoalConsistency         GoalOrientation = "consistency"
	GoalAggressiveGrowth    GoalOrientation = "aggressive_growth"
	GoalLowStress           GoalOrientation = "low_stress"
	GoalHighProbabilityOnly GoalOrientation = "high_probability_only"
	GoalFewerHighQuality    GoalOrientation = "fewer_high_quality"
)

// ---------------------------------------------------------------------------
// Section 14 — Trade Management
// ---------------------------------------------------------------------------

type PartialTPStyle string

const (
	PartialTPDisabled   PartialTPStyle = "disabled"
	PartialTPAggressive PartialTPStyle = "aggressive"
	PartialTPBalanced   PartialTPStyle = "balanced"
	PartialTPLetRun     PartialTPStyle = "let_run"
)

type TrailingStopBehaviour string

const (
	TrailingDisabled  TrailingStopBehaviour = "disabled"
	TrailingStructure TrailingStopBehaviour = "structure_based"
	TrailingATR       TrailingStopBehaviour = "atr_based"
	TrailingFixed     TrailingStopBehaviour = "fixed_pips"
)

type BreakEvenTrigger string

const (
	BETriggerDisabled   BreakEvenTrigger = "disabled"
	BETriggerAtTP1      BreakEvenTrigger = "at_tp1"
	BETriggerAt1RR      BreakEvenTrigger = "at_1rr"
	BETriggerAtMidpoint BreakEvenTrigger = "at_midpoint"
)

type TradeManagement struct {
	PartialTPStyle   PartialTPStyle        `json:"partial_tp_style"`
	TrailingStop     TrailingStopBehaviour `json:"trailing_stop"`
	BreakEvenTrigger BreakEvenTrigger      `json:"break_even_trigger"`
	ScaleInEnabled   bool                  `json:"scale_in_enabled"`
	ScaleOutEnabled  bool                  `json:"scale_out_enabled"`
	HoldRunners      bool                  `json:"hold_runners"`
	CloseBeforeNews  bool                  `json:"close_before_news"`
}

// ---------------------------------------------------------------------------
// Profile — the full 14-section trading operating system
// ---------------------------------------------------------------------------

// Profile is the canonical structured user trading operating system.
// It is persisted as JSONB and serialised verbatim to the engine on
// every analysis cycle. Adding a new field here requires bumping the
// schema_version constant below so the engine's context builder can
// reject older payloads it does not understand.
type Profile struct {
	SchemaVersion int                      `json:"schema_version"`
	Identity      Identity                 `json:"identity"`
	Style         TradingStyle             `json:"style"`
	Sessions      SessionPreferences       `json:"sessions"`
	Risk          RiskPersonality          `json:"risk"`
	Confirmation  ConfirmationStrictness   `json:"confirmation"`
	Structural    StructuralPreferences    `json:"structural"`
	Entry         EntryPreferences         `json:"entry"`
	Filtering     TradeFiltering           `json:"filtering"`
	Psychology    PsychologicalConstraints `json:"psychology"`
	Confluence    ConfluenceWeights        `json:"confluence"`
	Automation    AutomationPreferences    `json:"automation"`
	Assets        AssetPreferences         `json:"assets"`
	Goal          GoalOrientation          `json:"goal"`
	Management    TradeManagement          `json:"management"`
}

// CurrentSchemaVersion is bumped any time a backwards-incompatible
// field is added or removed from Profile.
const CurrentSchemaVersion = 1

// ---------------------------------------------------------------------------
// Record — the persisted row
// ---------------------------------------------------------------------------

// Record is the gateway-side representation of a single row in
// user_trading_systems. UserID is the PK; we keep exactly one row per
// user and overwrite on save / regenerate.
type Record struct {
	UserID    string    `json:"user_id"`
	Status    Status    `json:"status"`
	Version   int       `json:"version"`
	Profile   *Profile  `json:"profile,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// StatusView is the lightweight projection returned by GET
// /api/v1/trading-system/status. It deliberately omits the heavy
// profile blob so the dashboard onboarding checklist can poll cheaply
// on every mount without hydrating a multi-kilobyte JSON document.
//
// UpdatedAt is a *time.Time, not a value-type time.Time, because Go's
// encoding/json does NOT honour json:",omitempty" for value-type
// time.Time (the zero value 0001-01-01T00:00:00Z still serialises).
// A nil pointer correctly omits the field for users who have no row.
type StatusView struct {
	Status     Status     `json:"status"`
	Version    int        `json:"version"`
	UpdatedAt  *time.Time `json:"updated_at,omitempty"`
	HasProfile bool       `json:"has_profile"`
}
