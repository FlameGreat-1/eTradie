package models

// ProcessorInput is the payload sent to the Processor LLM.
// Combines TA output, Macro output, and RAG-retrieved knowledge.
//
// CONTRACT SOURCE OF TRUTH: proto/processor/v1/processor.proto
//
// If you add, remove, or rename a field here, you MUST also update:
//   1. proto/processor/v1/processor.proto (the contract)
//   2. src/engine/processor/models/io.py (Python side)
//   3. Run `make contract-check` to verify parity
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
//
// CONTRACT SOURCE OF TRUTH: proto/processor/v1/processor.proto
//
// If you add, remove, or rename a field here, you MUST also update:
//   1. proto/processor/v1/processor.proto (the contract)
//   2. src/engine/processor/models/io.py (Python side)
//   3. Run `make contract-check` to verify parity
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
}
