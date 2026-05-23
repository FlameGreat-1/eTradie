package context

import (
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
)

// Assembler builds the final ProcessorInput payload by combining
// TA output, Macro output, and RAG-retrieved knowledge.
type Assembler struct {
	log zerolog.Logger
}

// NewAssembler creates a ContextAssembler.
func NewAssembler() *Assembler {
	return &Assembler{log: observability.Logger("context_assembler")}
}

// Assemble builds ProcessorInput from all pipeline outputs.
// ragBundle is the raw JSON-decoded context bundle from the Python RAG service.
func (a *Assembler) Assemble(
	symbol string,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	ragBundle map[string]interface{},
	traceID string,
) *models.ProcessorInput {
	taAnalysis := buildTASection(taResult)
	macroAnalysis := buildMacroSection(macroResult)

	// Extract enriched macro signals for metadata.
	macroSignals := querybuilder.ExtractMacroSignals(macroResult)

	var availableDatasets []string
	if macroResult != nil {
		availableDatasets = macroResult.AvailableDatasets()
	}

	metadata := map[string]interface{}{
		"symbol":                   symbol,
		"htf_timeframes":           taResult.HTFTimeframes,
		"ltf_timeframes":           taResult.LTFTimeframes,
		"overall_trend":            taResult.OverallTrend,
		"macro_datasets_available": availableDatasets,
		"trace_id":                 traceID,
	}

	// Enriched macro metadata for the processor LLM.
	if macroSignals.RiskEnvironment != "" {
		metadata["risk_environment"] = macroSignals.RiskEnvironment
	}
	metadata["stagflation_detected"] = macroSignals.StagflationDetected
	metadata["safe_haven_elevated"] = macroSignals.SafeHavenElevated
	metadata["commodity_currencies_weak"] = macroSignals.CommodityCurrenciesWeak
	if macroSignals.DXYMomentum != "" {
		metadata["dxy_momentum"] = macroSignals.DXYMomentum
	}
	if macroSignals.DXYBias != "" {
		metadata["dxy_bias"] = macroSignals.DXYBias
	}
	metadata["cot_extremes_count"] = len(macroSignals.COTExtremesFlagged)
	if len(macroSignals.COTExtremesFlagged) > 0 {
		metadata["cot_extremes_currencies"] = macroSignals.COTExtremesFlagged
	}
	metadata["has_tff_data"] = macroSignals.COTHasTFFData
	metadata["has_qe_qt"] = macroSignals.HasQEQT
	if macroSignals.HasQEQT {
		metadata["qe_qt_action"] = macroSignals.QEQTAction
		metadata["qe_qt_bank"] = macroSignals.QEQTBank
		metadata["balance_sheet_direction"] = macroSignals.BalanceSheetDir
	}
	metadata["has_core_inflation"] = len(macroSignals.CoreInflationData) > 0
	metadata["has_iron_ore"] = macroSignals.IronOre != nil
	metadata["has_dairy_gdt"] = macroSignals.DairyGDT != nil

	// Propagate RAG metadata if present in the bundle.
	for _, key := range []string{"strategy_used", "coverage_result", "conflict_result", "total_chunks_returned", "coverage_gaps", "conflict_details"} {
		if v, ok := ragBundle[key]; ok {
			metadata["rag_"+key] = v
		}
	}

	payload := &models.ProcessorInput{
		Symbol:             symbol,
		TAAnalysis:         taAnalysis,
		MacroAnalysis:      macroAnalysis,
		RetrievedKnowledge: ragBundle,
		Metadata:           metadata,
	}

	var macroDatasetsCount int
	if macroResult != nil {
		macroDatasetsCount = len(macroResult.AvailableDatasets())
	}

	a.log.Debug().
		Str("symbol", symbol).
		Int("ta_smc_count", len(taResult.SMCCandidates)).
		Int("ta_snd_count", len(taResult.SnDCandidates)).
		Int("macro_datasets", macroDatasetsCount).
		Str("risk_environment", macroSignals.RiskEnvironment).
		Bool("stagflation", macroSignals.StagflationDetected).
		Str("dxy_momentum", macroSignals.DXYMomentum).
		Int("cot_extremes", len(macroSignals.COTExtremesFlagged)).
		Bool("has_qe_qt", macroSignals.HasQEQT).
		Str("trace_id", traceID).
		Msg("context_assembled")

	return payload
}

func buildTASection(ta *models.TASymbolResult) map[string]interface{} {
	return map[string]interface{}{
		"symbol":         ta.Symbol,
		"htf_timeframes": ta.HTFTimeframes,
		"ltf_timeframes": ta.LTFTimeframes,
		"status":         ta.Status,
		"smc_candidates": ta.SMCCandidates,
		"snd_candidates": ta.SnDCandidates,
		"snapshots":      ta.Snapshots,
		"alignment":      ta.Alignment,
		"overall_trend":  ta.OverallTrend,
	}
}

func buildMacroSection(macro *models.MacroResult) map[string]interface{} {
	if macro == nil {
		return map[string]interface{}{}
	}
	return map[string]interface{}{
		"central_bank":       macro.CentralBank,
		"cot":                macro.COT,
		"economic":           macro.Economic,
		"calendar":           macro.Calendar,
		"dxy":                macro.DXY,
		"intermarket":        macro.Intermarket,
		"sentiment":          macro.Sentiment,
		"datasets_available": macro.AvailableDatasets(),
		"collection_errors":  macro.Errors,
	}
}
