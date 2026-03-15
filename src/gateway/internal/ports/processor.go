package ports

import (
	"context"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
)

// ProcessorPort is the abstract interface for the Processor LLM.
// The gateway calls this to get a trade decision. The implementation
// sends the context to an LLM and parses the structured response.
// Follows the Dependency Inversion Principle.
type ProcessorPort interface {
	Process(ctx context.Context, input *models.ProcessorInput) (*models.ProcessorOutput, error)
}
