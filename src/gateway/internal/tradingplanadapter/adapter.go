// Package tradingplanadapter wires the trading-plan handler's narrow
// interfaces (tradingplan.EngineDispatcher, tradingplan.BalanceProvider)
// to the existing gateway infrastructure (infra.EngineHTTPClient).
//
// The package exists so the tradingplan package itself never imports
// infra. That keeps the handler unit-testable with table-driven fakes
// and keeps the dependency graph one-directional:
//
//   tradingplan      -> (interface declarations)
//   tradingplanadapter -> tradingplan + infra (concrete implementations)
//   main.go          -> tradingplan + tradingplanadapter (composition)
package tradingplanadapter

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/tradingplan"
)

// Dispatcher is the concrete tradingplan.EngineDispatcher. It POSTs
// the generation request to the engine's /internal/trading-plan/dispatch
// endpoint, which schedules the LLM job on the engine's background
// task coordinator and returns 202 Accepted.
//
// Dispatch returns quickly (well under a second on the happy path)
// because the engine endpoint never blocks on the LLM call — it
// returns as soon as the background job is queued. A non-nil error
// from Dispatch indicates a true server-side problem (the engine is
// down, mis-configured, or rejected the secret); the handler maps it
// to a row-level 'failed' state.
type Dispatcher struct {
	engine *infra.EngineHTTPClient
	log    zerolog.Logger
}

// NewDispatcher builds a Dispatcher.
func NewDispatcher(engine *infra.EngineHTTPClient, log zerolog.Logger) *Dispatcher {
	return &Dispatcher{engine: engine, log: log}
}

// Dispatch satisfies tradingplan.EngineDispatcher.
func (d *Dispatcher) Dispatch(ctx context.Context, req tradingplan.GenerationRequest) error {
	if d.engine == nil {
		return fmt.Errorf("trading-plan engine client is not configured")
	}

	// Body shape must match engine/routers/trading_plan.py::DispatchBody.
	var profile map[string]interface{}
	if len(req.ProfileJSON) > 0 {
		if err := json.Unmarshal(req.ProfileJSON, &profile); err != nil {
			return fmt.Errorf("unmarshal profile for dispatch: %w", err)
		}
	}

	body := map[string]interface{}{
		"user_id":          req.UserID,
		"balance":          req.Balance,
		"balance_currency": req.BalanceCurrency,
		"balance_source":   string(req.BalanceSource),
		"profile_version":  req.ProfileVersion,
		"profile":          profile,
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

	if _, err := d.engine.PostJSON(ctx, "/internal/trading-plan/dispatch", body); err != nil {
		d.log.Warn().
			Str("user_id", req.UserID).
			Err(err).
			Msg("trading_plan_dispatch_post_failed")
		return err
	}
	return nil
}

// Balance is the concrete tradingplan.BalanceProvider. It GETs the
// engine's existing /internal/broker/account_info endpoint, which
// already implements a Stale-While-Revalidate failover (Redis cache),
// so transient broker outages do not produce errors here.
//
// Returns (0, "", "fallback", nil) when:
//
//   - the engine reports no broker connection,
//   - the balance is zero or missing,
//   - the call fails for any reason (network, timeout, decode).
//
// Returning the fallback source on failure (rather than an error) is
// the documented contract per tradingplan.BalanceProvider — plan
// generation must never be blocked by a broker outage.
type Balance struct {
	engine *infra.EngineHTTPClient
	log    zerolog.Logger
}

// NewBalance builds a Balance provider.
func NewBalance(engine *infra.EngineHTTPClient, log zerolog.Logger) *Balance {
	return &Balance{engine: engine, log: log}
}

// GetBalance satisfies tradingplan.BalanceProvider.
func (b *Balance) GetBalance(
	ctx context.Context,
	userID string,
) (amount float64, currency string, source tradingplan.BalanceSource, err error) {
	if b.engine == nil || userID == "" {
		return 0, "", tradingplan.BalanceSourceFallback, nil
	}

	// Same trick as Dispatch: inject minimal claims so the shared
	// engine client attaches the X-User-Id header.
	ctx = auth.InjectClaimsIntoContext(ctx, &auth.Claims{UserID: userID})

	resp, callErr := b.engine.GetJSON(ctx, "/internal/broker/account_info")
	if callErr != nil {
		b.log.Debug().
			Str("user_id", userID).
			Err(callErr).
			Msg("trading_plan_balance_lookup_failed_falling_back")
		return 0, "", tradingplan.BalanceSourceFallback, nil
	}

	// account_info response shape:
	//   { balance, equity, margin, margin_free, currency }
	amt, _ := resp["balance"].(float64)
	ccy, _ := resp["currency"].(string)
	if amt <= 0 || ccy == "" {
		return 0, "", tradingplan.BalanceSourceFallback, nil
	}
	return amt, ccy, tradingplan.BalanceSourceBroker, nil
}
