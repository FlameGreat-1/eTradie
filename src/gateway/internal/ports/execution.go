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
}
