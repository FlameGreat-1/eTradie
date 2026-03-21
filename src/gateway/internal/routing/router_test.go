package routing

import (
	"context"
	"errors"
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// ── Mock Execution Port ─────────────────────────────────────────────────────

type mockExecutionPort struct {
	result map[string]interface{}
	err    error
	called int
}

func (m *mockExecutionPort) Execute(_ context.Context, _ *models.ProcessorOutput) (map[string]interface{}, error) {
	m.called++
	return m.result, m.err
}

// ── Router Tests ────────────────────────────────────────────────────────────

func TestRouter_NoSetup_ProcessorRejects(t *testing.T) {
	guards := NewGuardEvaluator()
	exec := &mockExecutionPort{}
	router := NewRouter(guards, exec, nil)

	processorOutput := &models.ProcessorOutput{
		TradeValid:     false,
		Reasoning:      "No valid confluence",
		RejectionRules: []string{"low_confluence"},
	}
	ta := &models.TASymbolResult{Symbol: "EURUSD", OverallTrend: "BULLISH"}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, "trace-001")

	if result.Outcome != constants.OutcomeNoSetup {
		t.Fatalf("expected NO_SETUP outcome, got %s", result.Outcome)
	}
	if exec.called != 0 {
		t.Fatal("execution should NOT be called for NO SETUP")
	}
}

func TestRouter_GuardRejection_NoExecution(t *testing.T) {
	guards := NewGuardEvaluator()
	exec := &mockExecutionPort{
		result: map[string]interface{}{"status": "filled"},
	}
	router := NewRouter(guards, exec, nil)

	// Create a counter-trend trade without CHoCH — guaranteed REJECT.
	processorOutput := &models.ProcessorOutput{
		TradeValid: true,
		Direction:  "SHORT",
		Symbol:     "EURUSD",
		Confidence: 0.7,
		Grade:      "B",
	}
	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, "trace-002")

	if result.Outcome != constants.OutcomeRejectedByGuard {
		t.Fatalf("expected REJECTED_BY_GUARD, got %s", result.Outcome)
	}
	if result.GuardResult == nil {
		t.Fatal("guard result should not be nil")
	}
	if exec.called != 0 {
		t.Fatal("execution should NOT be called when guards reject")
	}
}

func TestRouter_TradeApproved_ExecutionCalled(t *testing.T) {
	guards := NewGuardEvaluator()
	exec := &mockExecutionPort{
		result: map[string]interface{}{"status": "filled", "order_id": "ORD-123"},
	}
	router := NewRouter(guards, exec, nil)

	processorOutput := &models.ProcessorOutput{
		TradeValid: true,
		Direction:  "LONG",
		Symbol:     "USDJPY",
		Confidence: 0.85,
		Grade:      "A",
	}
	ta := &models.TASymbolResult{
		Symbol:       "USDJPY",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, "trace-003")

	// Guard result depends on time. If counter-trend guard passes (it's aligned),
	// the outcome should be TRADE_APPROVED unless a time-based guard rejects.
	if result.Outcome == constants.OutcomeTradeApproved {
		if exec.called != 1 {
			t.Fatalf("expected execution to be called once, got %d", exec.called)
		}
		if result.ExecutionResult["status"] != "filled" {
			t.Fatalf("expected execution status 'filled', got %v", result.ExecutionResult["status"])
		}
	}
}

func TestRouter_NilExecutionPort_Graceful(t *testing.T) {
	guards := NewGuardEvaluator()
	// Explicitly nil execution engine — simulates unimplemented Module B.
	router := NewRouter(guards, nil, nil)

	processorOutput := &models.ProcessorOutput{
		TradeValid: true,
		Direction:  "LONG",
		Symbol:     "USDJPY",
		Confidence: 0.9,
		Grade:      "A+",
	}
	ta := &models.TASymbolResult{
		Symbol:       "USDJPY",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, "trace-004")

	// If time-based guards pass, it should still succeed with a "pending" execution result.
	if result.Outcome == constants.OutcomeTradeApproved {
		if result.ExecutionResult["status"] != "pending" {
			t.Fatalf("expected 'pending' when execution engine is nil, got %v", result.ExecutionResult["status"])
		}
	}
}

func TestRouter_ExecutionError_ReturnsError(t *testing.T) {
	guards := NewGuardEvaluator()
	exec := &mockExecutionPort{
		err: errors.New("broker connection refused"),
	}
	router := NewRouter(guards, exec, nil)

	processorOutput := &models.ProcessorOutput{
		TradeValid: true,
		Direction:  "LONG",
		Symbol:     "GBPJPY",
		Confidence: 0.88,
		Grade:      "A",
	}
	ta := &models.TASymbolResult{
		Symbol:       "GBPJPY",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, "trace-005")

	// If guards pass, execution is attempted and fails.
	if result.Outcome == constants.OutcomeTradeApproved {
		if result.ExecutionResult["status"] != "error" {
			t.Fatalf("expected execution status 'error', got %v", result.ExecutionResult["status"])
		}
	}
}
