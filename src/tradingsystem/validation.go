package tradingsystem

import (
	"fmt"
	"strings"
)

// ValidationError is returned by Validate when the submitted profile
// violates one or more guardrails. The Field slice is suitable for the
// SPA to render inline field-level errors next to each section.
type ValidationError struct {
	Message string            `json:"message"`
	Fields  map[string]string `json:"fields,omitempty"`
}

func (e *ValidationError) Error() string {
	return e.Message
}

func newValidationError(msg string) *ValidationError {
	return &ValidationError{Message: msg, Fields: make(map[string]string)}
}

func (e *ValidationError) add(field, msg string) *ValidationError {
	e.Fields[field] = msg
	return e
}

func (e *ValidationError) hasFields() bool {
	return len(e.Fields) > 0
}

// Validate enforces the institutional guardrails PRACTICE.md mandates:
//
//   - every enum is one of the recognised values,
//   - numeric ranges are sane (no 0.01% risk, no 50x leverage requests),
//   - irrational combinations are rejected (e.g. fully-automatic
//     execution + strict confirmation only on a 1-minute scalp),
//   - empty multi-selects that the LLM needs (frameworks, asset
//     classes) get explicit defaults instead of being passed as `[]`.
//
// The function mutates the profile in place to normalise inputs
// (upper-cases preferred pairs, trims duplicates) before returning so
// callers can persist the cleaned value directly.
func Validate(p *Profile) error {
	if p == nil {
		return newValidationError("profile is required")
	}
	errs := newValidationError("trading system profile is invalid")

	// -- Section 1: Identity --------------------------------------------
	switch p.Identity.Experience {
	case ExperienceBeginner, ExperienceIntermediate, ExperienceAdvanced:
	default:
		errs.add("identity.experience", "must be beginner, intermediate, or advanced")
	}
	switch p.Identity.Automation {
	case AutomationManual, AutomationSemiAutomated, AutomationFullyAutomated:
	default:
		errs.add("identity.automation", "must be manual, semi_automated, or fully_automated")
	}
	switch p.Identity.RiskAppetite {
	case RiskAppetiteConservative, RiskAppetiteBalanced, RiskAppetiteAggressive:
	default:
		errs.add("identity.risk_appetite", "must be conservative, balanced, or aggressive")
	}
	switch p.Identity.TraderType {
	case TraderTypePrecision, TraderTypeFrequent:
	default:
		errs.add("identity.trader_type", "must be precision or frequent")
	}
	switch p.Identity.Discipline {
	case DisciplineRuleBased, DisciplineFlexibleDiscretion:
	default:
		errs.add("identity.discipline", "must be rule_based or flexible_discretion")
	}

	// -- Section 2: Style -----------------------------------------------
	switch p.Style {
	case StyleScalping, StyleIntraday, StyleSwing, StylePositional:
	default:
		errs.add("style", "must be scalping, intraday, swing, or positional")
	}

	// -- Section 3: Sessions --------------------------------------------
	if len(p.Sessions.PreferredSessions) == 0 {
		errs.add("sessions.preferred_sessions", "select at least one trading session")
	} else {
		seen := make(map[Session]bool, len(p.Sessions.PreferredSessions))
		cleaned := make([]Session, 0, len(p.Sessions.PreferredSessions))
		for _, s := range p.Sessions.PreferredSessions {
			switch s {
			case SessionAsian, SessionLondon, SessionNewYork, SessionLondonNYOverlap:
				if !seen[s] {
					seen[s] = true
					cleaned = append(cleaned, s)
				}
			default:
				errs.add("sessions.preferred_sessions", fmt.Sprintf("unknown session %q", string(s)))
			}
		}
		p.Sessions.PreferredSessions = cleaned
	}

	// -- Section 4: Risk ------------------------------------------------
	switch p.Risk.RiskModel {
	case RiskModelFixed, RiskModelAdaptive:
	default:
		errs.add("risk.risk_model", "must be fixed or adaptive")
	}
	if p.Risk.FixedRiskPercent < 0.1 || p.Risk.FixedRiskPercent > 3.0 {
		errs.add("risk.fixed_risk_percent", "must be between 0.1 and 3.0")
	}
	if p.Risk.MaxDailyDrawdownPercent < 1.0 || p.Risk.MaxDailyDrawdownPercent > 10.0 {
		errs.add("risk.max_daily_drawdown_percent", "must be between 1.0 and 10.0")
	}
	if p.Risk.MaxWeeklyDrawdownPercent < 2.0 || p.Risk.MaxWeeklyDrawdownPercent > 20.0 {
		errs.add("risk.max_weekly_drawdown_percent", "must be between 2.0 and 20.0")
	}
	if p.Risk.MaxWeeklyDrawdownPercent < p.Risk.MaxDailyDrawdownPercent {
		errs.add("risk.max_weekly_drawdown_percent", "weekly drawdown must be >= daily drawdown")
	}
	if p.Risk.MaxSimultaneousTrades < 1 || p.Risk.MaxSimultaneousTrades > 10 {
		errs.add("risk.max_simultaneous_trades", "must be between 1 and 10")
	}
	if p.Risk.MaxCorrelatedExposure < 1 || p.Risk.MaxCorrelatedExposure > 5 {
		errs.add("risk.max_correlated_exposure", "must be between 1 and 5")
	}
	if p.Risk.MaxCorrelatedExposure > p.Risk.MaxSimultaneousTrades {
		errs.add("risk.max_correlated_exposure", "cannot exceed max simultaneous trades")
	}

	// -- Section 5: Confirmation ----------------------------------------
	switch p.Confirmation {
	case ConfirmationAggressive, ConfirmationBalanced, ConfirmationStrict:
	default:
		errs.add("confirmation", "must be aggressive, balanced, or strict")
	}

	// -- Section 6: Structural ------------------------------------------
	if len(p.Structural.Frameworks) == 0 {
		errs.add("structural.frameworks", "select at least one structural framework")
	} else {
		seen := make(map[StructuralFramework]bool, len(p.Structural.Frameworks))
		cleaned := make([]StructuralFramework, 0, len(p.Structural.Frameworks))
		for _, f := range p.Structural.Frameworks {
			switch f {
			case FrameworkSMC, FrameworkSnD, FrameworkWyckoff, FrameworkLiquidity:
				if !seen[f] {
					seen[f] = true
					cleaned = append(cleaned, f)
				}
			default:
				errs.add("structural.frameworks", fmt.Sprintf("unknown framework %q", string(f)))
			}
		}
		p.Structural.Frameworks = cleaned
	}
	switch p.Structural.StructureEmphasis {
	case "low", "medium", "high":
	case "":
		p.Structural.StructureEmphasis = "medium"
	default:
		errs.add("structural.structure_emphasis", "must be low, medium, or high")
	}

	// -- Section 7: Entry -----------------------------------------------
	switch p.Entry.ExecutionMode {
	case EntryLimitOnly, EntryMarketAllowed, EntryEitherAllowed:
	default:
		errs.add("entry.execution_mode", "must be limit_only, market_allowed, or either_allowed")
	}

	// -- Section 8: Filtering -------------------------------------------
	if p.Filtering.MinimumRR < 1.0 || p.Filtering.MinimumRR > 10.0 {
		errs.add("filtering.minimum_rr", "must be between 1.0 and 10.0")
	}

	// -- Section 9: Psychology ------------------------------------------
	if p.Psychology.MaxLossesBeforeCooldown < 0 || p.Psychology.MaxLossesBeforeCooldown > 10 {
		errs.add("psychology.max_losses_before_cooldown", "must be between 0 and 10")
	}
	switch p.Psychology.EmotionalVolatilitySensitivity {
	case "low", "medium", "high":
	case "":
		p.Psychology.EmotionalVolatilitySensitivity = "medium"
	default:
		errs.add("psychology.emotional_volatility_sensitivity", "must be low, medium, or high")
	}

	// -- Section 10: Confluence weights (0..3 each) ---------------------
	for name, val := range map[string]int{
		"confluence.macro_alignment":  p.Confluence.MacroAlignment,
		"confluence.dxy":              p.Confluence.DXY,
		"confluence.cot":              p.Confluence.COT,
		"confluence.htf_alignment":    p.Confluence.HTFAlignment,
		"confluence.wyckoff":          p.Confluence.Wyckoff,
		"confluence.volume_liquidity": p.Confluence.VolumeLiquidity,
		"confluence.session_timing":   p.Confluence.SessionTiming,
	} {
		if val < 0 || val > 3 {
			errs.add(name, "weight must be between 0 and 3")
		}
	}

	// -- Section 11: Automation -----------------------------------------
	switch p.Automation.Mode {
	case AutoAlertOnly, AutoManualApproval, AutoSemiAutomatic, AutoFullyAutomatic:
	default:
		errs.add("automation.mode", "must be alert_only, manual_approval, semi_automatic, or fully_automatic")
	}

	// -- Section 12: Assets ---------------------------------------------
	if len(p.Assets.AssetClasses) == 0 {
		errs.add("assets.asset_classes", "select at least one asset class")
	} else {
		seen := make(map[AssetClass]bool, len(p.Assets.AssetClasses))
		cleaned := make([]AssetClass, 0, len(p.Assets.AssetClasses))
		for _, a := range p.Assets.AssetClasses {
			switch a {
			case AssetForex, AssetIndices, AssetGold, AssetCrypto, AssetVolatilityIndices:
				if !seen[a] {
					seen[a] = true
					cleaned = append(cleaned, a)
				}
			default:
				errs.add("assets.asset_classes", fmt.Sprintf("unknown asset class %q", string(a)))
			}
		}
		p.Assets.AssetClasses = cleaned
	}
	// Normalise preferred pairs: upper-case, trim, dedupe, cap at 50.
	if len(p.Assets.PreferredPairs) > 0 {
		seen := make(map[string]bool, len(p.Assets.PreferredPairs))
		cleaned := make([]string, 0, len(p.Assets.PreferredPairs))
		for _, raw := range p.Assets.PreferredPairs {
			sym := strings.ToUpper(strings.TrimSpace(raw))
			if sym == "" || seen[sym] {
				continue
			}
			if len(sym) > 16 {
				errs.add("assets.preferred_pairs", fmt.Sprintf("symbol %q is too long", sym))
				continue
			}
			seen[sym] = true
			cleaned = append(cleaned, sym)
			if len(cleaned) >= 50 {
				break
			}
		}
		p.Assets.PreferredPairs = cleaned
	}

	// -- Section 13: Goal -----------------------------------------------
	switch p.Goal {
	case GoalCapitalPreservation, GoalConsistency, GoalAggressiveGrowth,
		GoalLowStress, GoalHighProbabilityOnly, GoalFewerHighQuality:
	default:
		errs.add("goal", "invalid goal orientation")
	}

	// -- Section 14: Management -----------------------------------------
	switch p.Management.PartialTPStyle {
	case PartialTPDisabled, PartialTPAggressive, PartialTPBalanced, PartialTPLetRun:
	default:
		errs.add("management.partial_tp_style", "invalid partial TP style")
	}
	switch p.Management.TrailingStop {
	case TrailingDisabled, TrailingStructure, TrailingATR, TrailingFixed:
	default:
		errs.add("management.trailing_stop", "invalid trailing stop behaviour")
	}
	switch p.Management.BreakEvenTrigger {
	case BETriggerDisabled, BETriggerAtTP1, BETriggerAt1RR, BETriggerAtMidpoint:
	default:
		errs.add("management.break_even_trigger", "invalid break-even trigger")
	}

	// -- Cross-section institutional guardrails -------------------------
	// PRACTICE.md is explicit: the platform refuses to build irrational
	// systems. These checks live at the end so a single submission shows
	// every problem at once instead of the user playing whack-a-mole.

	// Scalping + fully-automatic + strict-only entries is a recipe for
	// rapid drawdown when the strict filter starves the bot of signals
	// and it widens its criteria mid-session.
	if p.Style == StyleScalping &&
		p.Automation.Mode == AutoFullyAutomatic &&
		p.Confirmation == ConfirmationStrict {
		errs.add("automation.mode",
			"scalping + fully_automatic + strict confirmation is not allowed; "+
				"choose semi_automatic, balanced confirmation, or a longer style")
	}

	// Aggressive scalping with a 1:>=3 minimum RR is mathematically
	// rarely satisfiable on intraday noise.
	if p.Style == StyleScalping && p.Filtering.MinimumRR >= 3.0 {
		errs.add("filtering.minimum_rr",
			"scalping rarely sustains RR >= 3; lower the floor or pick a longer style")
	}

	// Conservative risk personality with a high daily-drawdown cap is
	// inconsistent.
	if p.Identity.RiskAppetite == RiskAppetiteConservative &&
		p.Risk.MaxDailyDrawdownPercent > 4.0 {
		errs.add("risk.max_daily_drawdown_percent",
			"conservative profile cannot accept a daily drawdown above 4%")
	}

	// Fully-automatic execution + require_final_confirmation is
	// contradictory; the gateway honours the stricter of the two but
	// flagging it here keeps the stored profile coherent.
	if p.Automation.Mode == AutoFullyAutomatic && p.Automation.RequireFinalConfirmation {
		errs.add("automation.require_final_confirmation",
			"cannot require final user confirmation when mode is fully_automatic")
	}

	// Trailing-stop preference disagreement between risk and management
	// sections.
	if p.Risk.TrailingStopEnabled && p.Management.TrailingStop == TrailingDisabled {
		errs.add("management.trailing_stop",
			"risk profile enables trailing stop but management section disables it")
	}

	if errs.hasFields() {
		return errs
	}
	return nil
}
