package models

// ProcessorInput is the payload sent to the Processor LLM.
// Combines TA output, Macro output, and RAG-retrieved knowledge.
//
// CONTRACT SOURCE OF TRUTH: proto/engine/v1/engine.proto
// Proto message: ProcessLLMRequest (processor_input_json field)
//
// If you add, remove, or rename a field here, you MUST also update:
//  1. proto/engine/v1/engine.proto (ProcessLLMRequest)
//  2. src/engine/processor/models/io.py (Python side)
//  3. Run `make contract-check` to verify parity
type ProcessorInput struct {
	Symbol             string                 `json:"symbol"`
	TAAnalysis         map[string]interface{} `json:"ta_analysis"`
	MacroAnalysis      map[string]interface{} `json:"macro_analysis"`
	RetrievedKnowledge map[string]interface{} `json:"retrieved_knowledge"`
	Metadata           map[string]interface{} `json:"metadata"`
}

// ProcessorOutput is the decision returned by the Processor LLM.
// The gateway does NOT decide trade validity; the processor does.
// Guards run AFTER the processor to enforce hard safety rules.
// When guards pass, this is forwarded to Module B for execution.
//
// CONTRACT SOURCE OF TRUTH: proto/engine/v1/engine.proto
// Proto message: ProcessLLMResponse
//
// If you add, remove, or rename a field here, you MUST also update:
//  1. proto/engine/v1/engine.proto (ProcessLLMResponse)
//  2. src/engine/processor/models/io.py (Python side)
//  3. Run `make contract-check` to verify parity
type ProcessorOutput struct {
	TradeValid     bool                   `json:"trade_valid"`
	Direction      string                 `json:"direction,omitempty"`
	Symbol         string                 `json:"symbol,omitempty"`
	Confidence     float64                `json:"confidence"`
	Grade          string                 `json:"grade,omitempty"`
	RiskPercentage *float64               `json:"risk_percentage,omitempty"`
	Reasoning      string                 `json:"reasoning"`
	EntryPrice     *float64               `json:"entry_price,omitempty"`
	StopLoss       *float64               `json:"stop_loss,omitempty"`
	TakeProfit     *float64               `json:"take_profit,omitempty"`
	RejectionRules []string               `json:"rejection_rules"`
	RawResponse    map[string]interface{} `json:"raw_response"`

	// Execution-critical fields for Module B.
	// EntryPrice above is the midpoint (kept for backward compat with guards);
	// these provide the actual zone boundaries for limit order placement.
	EntryZoneLow  *float64 `json:"entry_zone_low,omitempty"`
	EntryZoneHigh *float64 `json:"entry_zone_high,omitempty"`

	// All three TP levels with position sizing percentages.
	// Module B needs these for partial close management.
	TP1Price *float64 `json:"tp1_price,omitempty"`
	TP1Pct   int      `json:"tp1_pct"`
	TP2Price *float64 `json:"tp2_price,omitempty"`
	TP2Pct   int      `json:"tp2_pct"`
	TP3Price *float64 `json:"tp3_price,omitempty"`
	TP3Pct   int      `json:"tp3_pct"`

	// Context required by Module B's pre-execution validator.
	TradingStyle    string   `json:"trading_style,omitempty"`
	Session         string   `json:"session,omitempty"`
	RRRatio         *float64 `json:"rr_ratio,omitempty"`
	ConfluenceScore float64  `json:"confluence_score"`
	AnalysisID      string   `json:"analysis_id,omitempty"`

	// Execution control: sent to Module B so it knows which mode to use
	// and whether the LTF confirmation already exists (pre-confirmed fast path).
	ExecutionMode string `json:"execution_mode,omitempty"` // "LIMIT" or "INSTANT"
	LTFConfirmed  bool   `json:"ltf_confirmed"`
	SetupType     string `json:"setup_type,omitempty"`
}
