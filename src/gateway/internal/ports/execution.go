package ports

import (
	"context"

	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// ExecutionPort is the abstract interface for the Execution Engine (Module B).
// The gateway depends on this abstraction. The actual execution engine will
// be implemented in a separate module and injected via the container.
type ExecutionPort interface {
	Execute(ctx context.Context, decision *models.ProcessorOutput) (map[string]interface{}, error)
	GetState(ctx context.Context, traceID string) (map[string]interface{}, error)
	CancelOrder(ctx context.Context, orderID, symbol, reason, traceID string) error

	// HaltState reads the kill-switch flags (CHECKLIST Section 8).
	// targetUserID selects whose per-user flag to read; empty means the
	// caller (the execution server resolves it from the JWT). Used by
	// the routing primary gate and the dashboard read path.
	HaltState(ctx context.Context, targetUserID string) (global bool, user bool, err error)

	// SetHaltState engages/releases a kill switch (CHECKLIST Section 8).
	// scope is "global" or "user". Authorization is enforced by the
	// execution server from the forwarded JWT. Returns the resulting
	// global + user state.
	SetHaltState(ctx context.Context, scope, targetUserID string, halted bool) (global bool, user bool, err error)
}
