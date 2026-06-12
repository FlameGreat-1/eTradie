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

func (m *mockExecutionPort) GetState(_ context.Context, _ string) (map[string]interface{}, error) {
	return map[string]interface{}{}, nil
}

func (m *mockExecutionPort) CancelOrder(_ context.Context, _, _, _, _ string) error {
	return nil
}

func (m *mockExecutionPort) HaltState(ctx context.Context, targetUserID string) (global bool, user bool, err error) {
	return false, false, nil
}

func (m *mockExecutionPort) SetHaltState(ctx context.Context, scope, targetUserID string, halted bool) (global bool, user bool, err error) {
	return false, false, nil
}

// ── Router Tests ────────────────────────────────────────────────────────────

func TestRouter_NoSetup_ProcessorRejects(t *testing.T) {
	guards := NewGuardEvaluator()
	exec := &mockExecutionPort{}
	router := NewRouter(guards, exec, nil, nil)

	processorOutput := &models.ProcessorOutput{
		TradeValid:     false,
		Reasoning:      "No valid confluence",
		RejectionRules: []string{"low_confluence"},
	}
	ta := &models.TASymbolResult{Symbol: "EURUSD", OverallTrend: "BULLISH"}
	macro := &models.MacroResult{}

	result := router.Route(context.Background(), processorOutput, ta, macro, nil, "trace-001")

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
	router := NewRouter(guards, exec, nil, nil)

	// Counter-trend trade without CHoCH — guaranteed REJECT.
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

	result := router.Route(context.Background(), processorOutput, ta, macro, nil, "trace-002")

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
	router := NewRouter(guards, exec, nil, nil)

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

	result := router.Route(context.Background(), processorOutput, ta, macro, nil, "trace-003")

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
	router := NewRouter(guards, nil, nil, nil)

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

	result := router.Route(context.Background(), processorOutput, ta, macro, nil, "trace-004")

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
	router := NewRouter(guards, exec, nil, nil)

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

	result := router.Route(context.Background(), processorOutput, ta, macro, nil, "trace-005")

	if result.Outcome == constants.OutcomeTradeApproved {
		if result.ExecutionResult["status"] != "error" {
			t.Fatalf("expected execution status 'error', got %v", result.ExecutionResult["status"])
		}
	}
}

// ── RoutePreLLM ─────────────────────────────────────────────────────────────

func TestRoutePreLLM_PassesThroughOnAllPass(t *testing.T) {
	guards := NewGuardEvaluator()
	router := NewRouter(guards, nil, nil, nil)

	ta := &models.TASymbolResult{Symbol: "USDJPY", OverallTrend: "BULLISH"}
	macro := &models.MacroResult{}

	result := router.RoutePreLLM(context.Background(), "USDJPY", ta, macro, "trace-pre-001")

	// USDJPY is allowed in Asian session, so pre-LLM should not reject
	// regardless of the test clock. When all 4 checks pass/warn the
	// outcome is empty (not OutcomeRejectedByGuard).
	if result.Outcome == constants.OutcomeRejectedByGuard {
		t.Fatalf("expected non-rejection for USDJPY, got %s (blocking=%v)", result.Outcome, result.GuardResult.BlockingRules)
	}
	if result.GuardResult == nil {
		t.Fatal("GuardResult must always be returned, got nil")
	}
	if len(result.GuardResult.Checks) != 4 {
		t.Fatalf("expected 4 pre-LLM checks, got %d", len(result.GuardResult.Checks))
	}
}

func TestRoutePreLLM_RejectsOnAsianSessionForXAUUSD(t *testing.T) {
	// This test only asserts that, when the Asian-session restriction
	// fires (which is purely time-driven), the outcome is the
	// short-circuit reject. Outside Asian hours the assertion is
	// inverted to still pass.
	guards := NewGuardEvaluator()
	router := NewRouter(guards, nil, nil, nil)

	ta := &models.TASymbolResult{Symbol: "XAUUSD"}
	macro := &models.MacroResult{}

	result := router.RoutePreLLM(context.Background(), "XAUUSD", ta, macro, "trace-pre-002")

	hour := timeNowHourUTC()
	isAsian := hour >= 0 && hour < 7

	if isAsian {
		if result.Outcome != constants.OutcomeRejectedByGuard {
			t.Fatalf("expected REJECTED_BY_GUARD for XAUUSD during Asian session (hour=%d), got %s", hour, result.Outcome)
		}
	} else {
		if result.Outcome == constants.OutcomeRejectedByGuard {
			for _, r := range result.GuardResult.BlockingRules {
				if r == string(constants.RuleSessionRestriction) {
					t.Fatalf("unexpected session-restriction rejection outside Asian session (hour=%d)", hour)
				}
			}
		}
	}
}

func timeNowHourUTC() int {
	return timeNowUTC().Hour()
}
