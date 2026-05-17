// Package performancereviewadapter wires the performance-review
// handler's narrow interfaces to the existing gateway infrastructure.
//
// The package exists so the performancereview package itself never
// imports infra. That keeps the handler unit-testable with table-
// driven fakes and keeps the dependency graph one-directional:
//
//   performancereview          -> (interface declarations)
//   performancereviewadapter   -> performancereview + infra (concrete)
//   main.go                    -> both (composition)
package performancereviewadapter

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/performancereview"
)

// Dispatcher is the concrete performancereview.EngineDispatcher. It
// POSTs the generation request to the engine's
// /internal/performance-review/dispatch endpoint, which schedules the
// LLM job on the engine's background-task coordinator and returns 202
// Accepted.
//
// Dispatch returns quickly (well under a second on the happy path)
// because the engine endpoint never blocks on the LLM call - it
// returns as soon as the background job is queued. A non-nil error
// indicates a true server-side problem (engine down, mis-configured,
// rejected secret); the handler maps it to a row-level 'failed' state.
type Dispatcher struct {
	engine *infra.EngineHTTPClient
	log    zerolog.Logger
}

// NewDispatcher builds a Dispatcher.
func NewDispatcher(engine *infra.EngineHTTPClient, log zerolog.Logger) *Dispatcher {
	return &Dispatcher{engine: engine, log: log}
}

// Dispatch satisfies performancereview.EngineDispatcher.
func (d *Dispatcher) Dispatch(
	ctx context.Context,
	req performancereview.GenerationRequest,
) error {
	if d.engine == nil {
		return fmt.Errorf("performance-review engine client is not configured")
	}

	// Body shape must match
	// engine/routers/performance_review.py::DispatchBody.
	body := map[string]interface{}{
		"user_id":         req.UserID,
		"period":          string(req.Period),
		"period_start":    req.PeriodStart,
		"period_end":      req.PeriodEnd,
		"profile_version": req.ProfileVersion,
	}

	// Inject minimal claims so the EngineHTTPClient attaches the
	// X-User-Id header automatically on the /internal path. We do
	// NOT have a full JWT here (this is gateway-internal background
	// work fired from the handler's goroutine), so we synthesise a
	// claims object with only the user_id populated. The engine's
	// verify_internal_auth dependency authenticates against the
	// shared secret; it does not inspect the JWT itself on this
	// surface, so additional claim fields would be unused.
	ctx = auth.InjectClaimsIntoContext(ctx, &auth.Claims{UserID: req.UserID})

	if _, err := d.engine.PostJSON(ctx, "/internal/performance-review/dispatch", body); err != nil {
		d.log.Warn().
			Str("user_id", req.UserID).
			Str("period", string(req.Period)).
			Err(err).
			Msg("performance_review_dispatch_post_failed")
		return err
	}
	return nil
}
