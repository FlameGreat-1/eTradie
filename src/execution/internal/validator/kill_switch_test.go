package validator

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// ── Check 0: Kill Switch (CHECKLIST Section 8) ──────────────────────────────
//
// check0KillSwitch is a pure function over RuntimeParams, so it is
// tested directly with no broker or DB, matching the convention in
// checks_test.go.

func TestCheck0_NeitherHalted_Pass(t *testing.T) {
	req := &models.TradeRequest{Symbol: "EURUSD"}
	params := &RuntimeParams{}
	result := check0KillSwitch(context.Background(), req, nil, params, nil, nil, time.Now())
	if !result.Passed {
		t.Fatalf("expected pass when neither switch is engaged, got: %s", result.Reason)
	}
}

func TestCheck0_GlobalHalted_Halt(t *testing.T) {
	req := &models.TradeRequest{Symbol: "EURUSD"}
	params := &RuntimeParams{GlobalTradingHalted: true}
	result := check0KillSwitch(context.Background(), req, nil, params, nil, nil, time.Now())
	if result.Passed {
		t.Fatal("expected HALTED when global switch is engaged")
	}
	if result.FailedCheck != constants.CheckKillSwitch {
		t.Fatalf("expected CheckKillSwitch, got %d", result.FailedCheck)
	}
	if result.Outcome != constants.OutcomeHalted {
		t.Fatalf("expected HALTED outcome, got %s", result.Outcome)
	}
	if !strings.Contains(result.Reason, "global") {
		t.Fatalf("expected global reason, got: %s", result.Reason)
	}
}

func TestCheck0_UserHalted_Halt(t *testing.T) {
	req := &models.TradeRequest{Symbol: "EURUSD"}
	params := &RuntimeParams{UserTradingHalted: true}
	result := check0KillSwitch(context.Background(), req, nil, params, nil, nil, time.Now())
	if result.Passed {
		t.Fatal("expected HALTED when user switch is engaged")
	}
	if result.FailedCheck != constants.CheckKillSwitch {
		t.Fatalf("expected CheckKillSwitch, got %d", result.FailedCheck)
	}
	if result.Outcome != constants.OutcomeHalted {
		t.Fatalf("expected HALTED outcome, got %s", result.Outcome)
	}
}

func TestCheck0_BothHalted_GlobalReasonWins(t *testing.T) {
	req := &models.TradeRequest{Symbol: "EURUSD"}
	params := &RuntimeParams{GlobalTradingHalted: true, UserTradingHalted: true}
	result := check0KillSwitch(context.Background(), req, nil, params, nil, nil, time.Now())
	if result.Passed {
		t.Fatal("expected HALTED when both switches are engaged")
	}
	if !strings.Contains(result.Reason, "global") {
		t.Fatalf("expected GLOBAL reason to win precedence, got: %s", result.Reason)
	}
}

func TestCheck0_NilParams_Pass(t *testing.T) {
	req := &models.TradeRequest{Symbol: "EURUSD"}
	result := check0KillSwitch(context.Background(), req, nil, nil, nil, nil, time.Now())
	if !result.Passed {
		t.Fatal("expected pass for nil params (defensive)")
	}
}
