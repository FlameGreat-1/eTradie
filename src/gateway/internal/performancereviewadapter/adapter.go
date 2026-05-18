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
//
// It reads the authenticated user's full claims from the supplied
// context (the handler injects them with auth.InjectClaimsIntoContext
// before launching the background dispatch goroutine) so the
// EngineHTTPClient can forward X-User-Tier and X-User-Role to the
// engine.
//
// The engine's performance-review generator enforces a strict
// BYOK-or-managed policy: a user must either have a personal LLM
// connection configured, OR be an admin / pro_managed user that can
// fall back to the platform key. Without the role and tier on the
// dispatch, the engine cannot tell whether to fall back or reject —
// which is exactly what was producing the
// "You must configure your own LLM API Key in Settings" error for
// admin users with no personal connection.
func (d *Dispatcher) Dispatch(
	ctx context.Context,
	req performancereview.GenerationRequest,
) error {
	if d.engine == nil {
		return fmt.Errorf("performance-review engine client is not configured")
	}

	// Resolve the identity to forward. Same priority as the trading-
	// plan adapter: full claims if present, otherwise synthesise from
	// the request's UserID.
	claims := auth.ClaimsFromContext(ctx)
	if claims == nil {
		claims = &auth.Claims{UserID: req.UserID}
	} else if claims.UserID == "" {
		cloned := *claims
		cloned.UserID = req.UserID
		claims = &cloned
	}

	// Body shape must match
	// engine/routers/performance_review.py::DispatchBody.
	body := map[string]interface{}{
		"user_id":         req.UserID,
		"period":          string(req.Period),
		"period_start":    req.PeriodStart,
		"period_end":      req.PeriodEnd,
		"profile_version": req.ProfileVersion,
		// Identity fields are also placed in the body for the same
		// reason as trading-plan: header-stripping intermediaries
		// must never be able to silently downgrade the dispatch to
		// 'no role / no tier'. Body wins over header on the engine.
		"role": string(claims.Role),
		"tier": claims.Tier,
	}

	ctx = auth.InjectClaimsIntoContext(ctx, claims)

	if _, err := d.engine.PostJSON(ctx, "/internal/performance-review/dispatch", body); err != nil {
		d.log.Warn().
			Str("user_id", req.UserID).
			Str("period", string(req.Period)).
			Str("role", string(claims.Role)).
			Str("tier", claims.Tier).
			Err(err).
			Msg("performance_review_dispatch_post_failed")
		return err
	}
	return nil
}
