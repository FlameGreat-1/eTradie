package ports

import (
	"context"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
)

// ExecutionPort is the abstract interface for the Execution Engine (Module B).
// The gateway depends on this abstraction. The actual execution engine will
// be implemented in a separate module and injected via the container.
type ExecutionPort interface {
	Execute(ctx context.Context, decision *models.ProcessorOutput) (map[string]interface{}, error)
}
