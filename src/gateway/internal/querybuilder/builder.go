package querybuilder

import (
	"sort"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// Builder translates TA + Macro outputs into RAG query parameters.
type Builder struct {
	log zerolog.Logger
}

// NewBuilder creates a QueryBuilder.
func NewBuilder() *Builder {
	return &Builder{log: observability.Logger("query_builder")}
}

// Build constructs RAGQueryParams for a single symbol.
func (b *Builder) Build(
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	style string,
	traceID string,
) *models.RAGQueryParams {
	taSignals := ExtractTASignals(taResult)
	macroSignals := ExtractMacroSignals(macroResult)

	queryText := BuildQueryText(taSignals, macroSignals)
	strategy := selectStrategy(taSignals, macroSignals)

	var primarySetupFamily string
	if len(taSignals.SetupFamilies) > 0 {
		primarySetupFamily = taSignals.SetupFamilies[0]
	}

	allFrameworks := collectAllFrameworks(taSignals, macroSignals)

	hasMacro := macroSignals.FedTone != "" || macroSignals.ECBTone != "" ||
		macroSignals.BOETone != "" || macroSignals.BOJTone != "" ||
		macroSignals.MacroBiasUSD != "" || macroSignals.HasQEQT ||
		macroSignals.StagflationDetected || macroSignals.RiskEnvironment != ""

	hasCOT := macroSignals.COTNetEUR != nil || macroSignals.COTNetGBP != nil ||
		macroSignals.COTNetJPY != nil || macroSignals.COTNetAUD != nil ||
		macroSignals.COTNetCAD != nil || macroSignals.COTNetNZD != nil ||
		macroSignals.COTNetCHF != nil || len(macroSignals.COTExtremesFlagged) > 0 ||
		macroSignals.COTHasTFFData

	hasDXY := macroSignals.DXYValue != nil || macroSignals.DXYMomentum != ""
	hasHighImpact := len(macroSignals.HighImpactEventsWithin24h) > 0

	var timeframe string
	if len(taSignals.HTFTimeframes) > 0 {
		timeframe = taSignals.HTFTimeframes[0]
	}

	params := &models.RAGQueryParams{
		QueryText:          queryText,
		Strategy:           strategy,
		Framework:          taSignals.Framework,
		SetupFamily:        primarySetupFamily,
		Direction:          taSignals.Direction,
		Timeframe:          timeframe,
		Style:              style,
		Symbol:             taResult.Symbol,
		AllFrameworks:      allFrameworks,
		AllSetupFamilies:   taSignals.SetupFamilies,
		HasSMCCandidates:   taSignals.HasBMS || taSignals.HasOrderBlock || taSignals.HasFVG || taSignals.HasLiquiditySweep,
		HasSnDCandidates:   taSignals.HasQML || taSignals.HasSRFlip || taSignals.HasRSFlip,
		HasMacroData:       hasMacro,
		HasCOTData:         hasCOT,
		HasRateDecision:    macroSignals.HasRateDecision || macroSignals.HasRateChange,
		HasHighImpactEvent: hasHighImpact,
		HasDXYData:         hasDXY,

		// Enriched macro signal fields for RAG retrieval optimization.
		HasQEQT:                    macroSignals.HasQEQT,
		HasStagflation:             macroSignals.StagflationDetected,
		HasCOTExtremes:             len(macroSignals.COTExtremesFlagged) > 0,
		HasTFFData:                 macroSignals.COTHasTFFData,
		HasCoreInflation:           len(macroSignals.CoreInflationData) > 0,
		HasSafeHavenElevated:       macroSignals.SafeHavenElevated,
		HasCommodityCurrenciesWeak: macroSignals.CommodityCurrenciesWeak,
		DXYMomentum:                macroSignals.DXYMomentum,
		RiskEnvironment:            macroSignals.RiskEnvironment,
	}

	b.log.Debug().
		Str("symbol", taResult.Symbol).
		Int("query_text_length", len(queryText)).
		Str("framework", params.Framework).
		Str("setup_family", params.SetupFamily).
		Strs("all_frameworks", allFrameworks).
		Strs("all_setup_families", taSignals.SetupFamilies).
		Str("direction", params.Direction).
		Str("strategy", params.Strategy).
		Int("patterns_count", len(taSignals.PatternsDetected)).
		Bool("has_smc", params.HasSMCCandidates).
		Bool("has_snd", params.HasSnDCandidates).
		Bool("has_macro", params.HasMacroData).
		Bool("has_cot", params.HasCOTData).
		Bool("has_dxy", params.HasDXYData).
		Bool("has_qe_qt", macroSignals.HasQEQT).
		Bool("stagflation", macroSignals.StagflationDetected).
		Int("cot_extremes", len(macroSignals.COTExtremesFlagged)).
		Bool("has_tff", macroSignals.COTHasTFFData).
		Str("risk_environment", macroSignals.RiskEnvironment).
		Str("dxy_momentum", macroSignals.DXYMomentum).
		Str("trace_id", traceID).
		Msg("rag_query_built")

	return params
}

func selectStrategy(ta *TASignals, macro *MacroSignals) string {
	if macro.HasNFP || macro.HasCPI || macro.HasRateDecision {
		return "rule_first"
	}
	if len(macro.HighImpactEventsWithin24h) > 0 {
		return "rule_first"
	}
	if macro.HasRateChange {
		return "rule_first"
	}
	if macro.HasQEQT {
		return "rule_first"
	}
	if macro.StagflationDetected {
		return "rule_first"
	}
	if len(macro.COTExtremesFlagged) > 0 {
		return "rule_first"
	}
	if ta.Framework != "" && len(ta.SetupFamilies) > 0 && ta.Direction != "" {
		return "scenario_first"
	}
	if macro.MacroBiasUSD != "" && macro.MacroBiasUSD != "NEUTRAL" {
		return "macro_bias"
	}
	return "hybrid"
}

func collectAllFrameworks(ta *TASignals, macro *MacroSignals) []string {
	frameworks := make(map[string]struct{})

	if ta.HasBMS || ta.HasChoCH || ta.HasSMS || ta.HasOrderBlock || ta.HasFVG || ta.HasLiquiditySweep || ta.HasInducementCleared || ta.HasDisplacement {
		frameworks["smc"] = struct{}{}
	}
	if ta.HasQML || ta.HasSRFlip || ta.HasRSFlip || ta.HasMPL || ta.HasFakeout || ta.HasMarubozu || ta.HasCompression {
		frameworks["snd"] = struct{}{}
	}

	frameworks["wyckoff"] = struct{}{}

	if macro.DXYValue != nil || macro.DXYTrend != "" || macro.DXYMomentum != "" {
		frameworks["dxy"] = struct{}{}
	}
	if macro.COTNetEUR != nil || macro.COTNetGBP != nil || macro.COTNetJPY != nil ||
		macro.COTNetAUD != nil || macro.COTNetCAD != nil || macro.COTNetNZD != nil ||
		macro.COTNetCHF != nil || len(macro.COTExtremesFlagged) > 0 || macro.COTHasTFFData {
		frameworks["cot"] = struct{}{}
	}
	if macro.FedTone != "" || macro.ECBTone != "" || macro.BOETone != "" || macro.BOJTone != "" || macro.HasQEQT {
		frameworks["macro"] = struct{}{}
	}
	if macro.IronOre != nil || macro.DairyGDT != nil || macro.Copper != nil ||
		macro.OilPrice != nil || macro.GoldPrice != nil || macro.NaturalGas != nil {
		frameworks["intermarket"] = struct{}{}
	}
	if macro.StagflationDetected || macro.SafeHavenElevated || macro.CommodityCurrenciesWeak ||
		(macro.RiskEnvironment != "" && macro.RiskEnvironment != "NEUTRAL") {
		frameworks["risk_environment"] = struct{}{}
	}

	out := make([]string, 0, len(frameworks))
	for k := range frameworks {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
