package monitoring

import (
	"context"
	goerrors "errors"
	"fmt"
	"math"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// StateReconciler keeps the Management engine's in-memory trade state
// aligned with the MT5 broker's reality. It performs a startup sync
// and watches positions via broker.Port.WatchPositions (polling under
// the hood, diff-detected at the broker boundary).
//
// One instance per (user_id, broker) pair. Identity is stamped at
// construction so background calls build claims-bearing contexts
// without re-parsing the JWT.
type StateReconciler struct {
	mgr       *Manager
	bp        broker.Port
	repo      *journal.Repository
	transport AlertTransport

	userID    string
	username  string
	role      string
	tier      string
	statusJWT string
	authToken string

	watchInterval time.Duration
	log           zerolog.Logger
}

// NewStateReconciler creates a reconciler for a specific user.
// `user` provides the identity; pass nil only when running unit tests
// against the mock broker. `watchInterval <= 0` falls back to 1s.
func NewStateReconciler(
	mgr *Manager,
	bp broker.Port,
	repo *journal.Repository,
	transport AlertTransport,
	user *auth.User,
	authToken string,
	watchInterval time.Duration,
) *StateReconciler {
	var userID, username, role, tier, statusJWT string
	if user != nil {
		userID = user.ID
		username = user.Username
		role = string(user.Role)
		tier = user.Tier
		statusJWT = user.Status
	}
	if watchInterval <= 0 {
		watchInterval = time.Second
	}
	return &StateReconciler{
		mgr:           mgr,
		bp:            bp,
		repo:          repo,
		transport:     transport,
		userID:        userID,
		username:      username,
		role:          role,
		tier:          tier,
		statusJWT:     statusJWT,
		authToken:     authToken,
		watchInterval: watchInterval,
		log:           observability.Logger("state_reconciler").With().Str("user_id", userID).Logger(),
	}
}

// authContext returns a context with the reconciler's owner identity
// injected as parsed *auth.Claims plus the raw service token for
// any legacy callee that still reads RawTokenFromContext.
func (s *StateReconciler) authContext(parent context.Context) context.Context {
	ctx := auth.InjectIdentity(
		parent,
		s.userID, s.username, auth.Role(s.role), s.tier, s.statusJWT,
	)
	if s.authToken != "" {
		ctx = auth.InjectTokenIntoContext(ctx, s.authToken)
	}
	return ctx
}

// RunStartupSync fetches all currently open MT5 positions for this user.
// If it finds a position that is not in the database, it imports it.
func (s *StateReconciler) RunStartupSync(ctx context.Context) error {
	s.log.Info().Msg("starting_startup_sync_for_user")

	tradeCtx := s.authContext(ctx)

	positions, err := s.bp.GetPositions(tradeCtx)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_fetch_broker_positions_for_sync")
		return err
	}

	// Get all currently managed trades from memory.
	managedTrades := s.mgr.GetAllTrades()
	
	// Create a fast lookup map of tickets we already know about.
	knownTickets := make(map[string]bool)
	for _, t := range managedTrades {
		t.RLock()
		if t.UserID == s.userID && t.BrokerOrderID != "" {
			knownTickets[t.BrokerOrderID] = true
		}
		t.RUnlock()
	}

	imported := 0
	for _, pos := range positions {
		if knownTickets[pos.Ticket] {
			continue // We already manage this trade.
		}

		trade, err := s.buildReconciledTrade(ctx, pos)
		if err != nil {
			s.log.Error().Err(err).Str("ticket", pos.Ticket).Msg("failed_to_build_reconciled_trade")
			continue
		}

		// Register with the manager so it gets actively monitored.
		s.mgr.RegisterTrade(trade)
		imported++
	}

	s.log.Info().Int("imported_trades", imported).Msg("startup_sync_complete_for_active_positions")

	// ---- Phase 2: History Sync ----
	// Fetch last 30 days of closed deals to rebuild the Journal if wiped.
	// Same tradeCtx so the bridge sees the identity-bearing context.
	history, err := s.bp.GetHistory(tradeCtx, 30)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_fetch_broker_history_for_sync")
		// Don't fail the whole startup if history fails
	} else {
		s.log.Info().Int("deals_found", len(history)).Msg("discovered_historical_deals_processing")
		historicalImported := 0
		for _, h := range history {
			// We only want closed positions that have a profit
			if h.Ticket == "" {
				continue
			}

			// Try to insert a dummy closed trade.
			// This is a rough approximation since we don't have entry/exit pairs matched perfectly by ticket.
			// The EA groups them by DEAL_ENTRY_OUT which gives us the final result.
			
			tradeID := "TMG-HIST-" + h.Ticket
			outcome := string(constants.OutcomeBreakeven)
			if h.Profit > 0 {
				outcome = string(constants.OutcomeWin)
			} else if h.Profit < 0 {
				outcome = string(constants.OutcomeLoss)
			}

			// We use the deal time as the closed at time
			closedAt := time.Unix(h.Time, 0).UTC()

			dbRecord := &journal.TradeRecord{
				UserID:           s.userID,
				TradeID:          tradeID,
				Symbol:           h.Symbol,
				Direction:        h.Direction,
				BrokerOrderID:    h.Ticket,
				TradingStyle:     string(constants.StyleIntraday),
				Grade:            "MANUAL/RESTORED",
				Origin:           journal.OriginManualRestored,
				EntryPrice:       0.0, // We don't have exact entry from the OUT deal
				StopLoss:         0.0,
				InitialSL:        0.0,
				TP1Price:         0.0,
				TotalLotSize:     h.Volume,
				Status:           string(constants.StatusClosed),
				OpenedAt:         closedAt.Add(-1 * time.Hour), // Rough approximation
				ClosedAt:         &closedAt,
				GrossPnL:         h.Profit,
				Outcome:          outcome,
				DurationMinutes:  60, // Rough approximation
			}

			// Ignore "duplicate key" errors if it already exists
			if err := s.repo.InsertTrade(ctx, dbRecord); err != nil {
				continue
			}
			historicalImported++
		}
		s.log.Info().Int("historical_imported", historicalImported).Msg("startup_history_sync_complete")
	}

	return nil
}

// RunStreamListener watches the user's broker positions via
// broker.Port.WatchPositions and reconciles every structurally-changed
// snapshot with in-memory trade state. WatchPositions polls under the
// hood; diff-detection at the broker boundary ensures this loop only
// does real work when something moved.
//
// Backoff strategy:
//   - ErrNoBrokerConfigured: exponential backoff up to 5m before
//     re-arming the watcher. Hammering the engine when the user has
//     not configured a broker is wasted load.
//   - Other errors: same exponential backoff, treated as transient.
//   - Successful frame: backoff resets to base.
func (s *StateReconciler) RunStreamListener(ctx context.Context) {
	s.log.Info().
		Dur("watch_interval", s.watchInterval).
		Msg("starting_position_watcher")

	const baseBackoff = 2 * time.Second
	const maxBackoff = 5 * time.Minute
	backoff := baseBackoff

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		tradeCtx := s.authContext(ctx)
		watchCtx, cancel := context.WithCancel(tradeCtx)
		positions, errCh := s.bp.WatchPositions(watchCtx, s.watchInterval)

		cycleErr := s.consumeWatch(tradeCtx, positions, errCh, func() {
			backoff = baseBackoff
		})
		cancel()

		if cycleErr == nil {
			// Parent context done; exit cleanly.
			return
		}

		if goerrors.Is(cycleErr, broker.ErrNoBrokerConfigured) {
			s.log.Info().
				Dur("backoff", backoff).
				Msg("no_broker_configured_backing_off")
		} else {
			s.log.Warn().
				Err(cycleErr).
				Dur("retry_in", backoff).
				Msg("position_watcher_failed_retrying")
		}

		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}

		if backoff < maxBackoff {
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
		}
	}
}

// consumeWatch reads from a single (positions, errors) channel pair
// until one side closes or yields an error. Returns nil when the
// parent context cancelled (clean shutdown), or the watcher error
// for the caller's backoff logic.
func (s *StateReconciler) consumeWatch(
	ctx context.Context,
	positions <-chan []broker.PositionInfo,
	errCh <-chan error,
	onFrame func(),
) error {
	for {
		select {
		case <-ctx.Done():
			return nil

		case err, ok := <-errCh:
			if !ok {
				return fmt.Errorf("position watcher ended unexpectedly")
			}
			return err

		case snapshot, ok := <-positions:
			if !ok {
				// Position channel closed; drain the error side once.
				select {
				case err := <-errCh:
					if err != nil {
						return err
					}
				default:
				}
				return fmt.Errorf("position channel closed")
			}
			s.processPositionUpdate(ctx, snapshot)
			if onFrame != nil {
				onFrame()
			}
		}
	}
}

func (s *StateReconciler) processPositionUpdate(ctx context.Context, positions []broker.PositionInfo) {
	managedTrades := s.mgr.GetAllTrades()
	
	// Create lookup maps
	brokerState := make(map[string]broker.PositionInfo)
	for _, p := range positions {
		brokerState[p.Ticket] = p
	}

	knownTickets := make(map[string]bool)
	for _, t := range managedTrades {
		t.RLock()
		if t.UserID == s.userID && t.BrokerOrderID != "" {
			knownTickets[t.BrokerOrderID] = true
		}
		t.RUnlock()
	}

	for _, t := range managedTrades {
		t.RLock()
		if t.UserID != s.userID || t.BrokerOrderID == "" {
			t.RUnlock()
			continue
		}
		
		ticket := t.BrokerOrderID
		dbSL := t.StopLoss
		dbTP := t.TP1Price
		dbRemaining := t.RemainingLotSize
		tp1Hit := t.TP1Hit
		tp2Hit := t.TP2Hit
		tp3Hit := t.TP3Hit
		breakevenSet := t.BreakevenSet
		tradeID := t.TradeID
		symbol := t.Symbol
		t.RUnlock()

		bPos, exists := brokerState[ticket]
		if !exists {
			// The position vanished from the broker (closed).
			// Trigger the close logic here using the last known current price.
			s.mgr.HandleExternalClose(ctx, t)
			s.mgr.RemoveTrade(tradeID)
			continue
		}

		// EM-M1: the broker is the source of truth for the open volume.
		// A partial close that fired at the broker while Module C was down
		// or lagging leaves dbRemaining stale; adopt the broker volume so
		// software TP sizing works off the real remaining lot. The
		// vanished-position branch above already handles the fully-closed
		// case, so only strictly positive broker volumes are adopted here.
		const lotEpsilon = 0.0009 // below the 0.01 min lot step
		if bPos.Volume > 0 {
			delta := dbRemaining - bPos.Volume
			if delta < 0 {
				delta = -delta
			}
			if delta > lotEpsilon {
				s.log.Warn().
					Str("ticket", ticket).
					Float64("engine_remaining", dbRemaining).
					Float64("broker_volume", bPos.Volume).
					Msg("remaining_volume_drift_adopting_broker_truth")
				t.Lock()
				t.RemainingLotSize = bPos.Volume
				t.Unlock()
				if err := s.repo.UpdateTradeRuntime(ctx, s.userID, tradeID, bPos.Volume, bPos.StopLoss, tp1Hit, tp2Hit, tp3Hit, breakevenSet); err != nil {
					s.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_runtime_volume_reconcile_failed")
				}
			}
		}

		if bPos.StopLoss != dbSL || bPos.TakeProfit != dbTP {
			s.log.Info().
				Str("ticket", ticket).
				Float64("old_sl", dbSL).Float64("new_sl", bPos.StopLoss).
				Float64("old_tp", dbTP).Float64("new_tp", bPos.TakeProfit).
				Msg("manual_broker_modification_detected")

			t.Lock()
			t.StopLoss = bPos.StopLoss
			t.Swap = bPos.Swap
			t.Commission = bPos.Commission
			if bPos.TakeProfit != 0 {
				t.TP1Price = bPos.TakeProfit
				// We don't overwrite TP2/TP3 as they are logical, but TP1 is the broker TP.
			}
			t.Unlock()

			// Persist the SL change to the journal
			_ = s.repo.UpdateTradeSL(ctx, s.userID, tradeID, bPos.StopLoss)

			// Publish an alert so the React dashboard updates its lines instantly
			s.transport.Publish(ctx, alert.NewEvent(
				alert.SourceTradeManager,
				alert.TypeTradeSynced,
				alert.SeverityInfo,
				"Manual MT5 Modification Synced",
			).WithUserID(s.userID).WithSymbol(symbol).WithDetail("new_sl", bPos.StopLoss).WithDetail("new_tp", bPos.TakeProfit))
		} else {
			// Even if SL/TP hasn't changed, continuously update Swap/Commission for dashboard
			t.Lock()
			t.Swap = bPos.Swap
			t.Commission = bPos.Commission
			t.Unlock()
		}
	}

	// Reconcile new orphaned positions (manually opened or triggered pending orders)
	for _, pos := range positions {
		if knownTickets[pos.Ticket] {
			continue // We already manage this trade.
		}

		trade, err := s.buildReconciledTrade(ctx, pos)
		if err != nil {
			s.log.Error().Err(err).Str("ticket", pos.Ticket).Msg("failed_to_build_new_reconciled_trade")
			continue
		}

		s.mgr.RegisterTrade(trade)

		s.transport.Publish(ctx, alert.NewEvent(
			alert.SourceTradeManager,
			alert.TypeTradeSynced,
			alert.SeverityInfo,
			"External Trade Reconciled",
		).WithUserID(s.userID).WithSymbol(trade.Symbol).WithDetail("ticket", pos.Ticket))
	}
}

// buildReconciledTrade turns a raw broker position into a managed Trade,
// preferring full plan recovery over a bare import (EM-F2).
//
// Resolution order:
//
//  1. RECOVER OUR OWN TRADE: if management_trades already holds a row for
//     this broker ticket (this user), the position is one of our system
//     trades that reached the broker but whose Module C handoff was
//     missed (e.g. a LIMIT fill whose NotifyExecutionCompleted failed).
//     Rebuild the in-memory Trade from that row so the REAL TP1/2/3+pct,
//     trading style, risk, rr and point/digits are restored. No new row
//     is inserted -- the row already exists.
//
//  2. GENUINELY MANUAL/EXTERNAL: no system row exists. Import a bare
//     Trade using constants.StyleManualDefault (POSITIONAL -- the safest
//     automated-interference profile) and persist it. The broker SL
//     becomes InitialSL and the broker TP becomes TP1; TP2/TP3 stay
//     unset because the trader expressed a single target. Every
//     management engine still runs; POSITIONAL only avoids the
//     intraday-specific 3h SL-tighten and 16:30 EOD hard-close.
//
// Identity fields are stamped from the reconciler so the worker's
// IdentityCtx builds the same claims-bearing context a gRPC-registered
// trade would.
func (s *StateReconciler) buildReconciledTrade(
	ctx context.Context,
	pos broker.PositionInfo,
) (*types.Trade, error) {
	// 1) Recover our own system trade by broker ticket.
	if rec, err := s.repo.GetTradeByBrokerOrderID(ctx, s.userID, pos.Ticket); err == nil && rec != nil {
		s.log.Info().
			Str("ticket", pos.Ticket).
			Str("symbol", pos.Symbol).
			Str("trade_id", rec.TradeID).
			Str("style", rec.TradingStyle).
			Msg("reconciled_position_matched_system_trade_recovering_full_plan")

		return &types.Trade{
			TradeID:          rec.TradeID,
			Symbol:           rec.Symbol,
			Direction:        constants.Direction(rec.Direction),
			BrokerOrderID:    rec.BrokerOrderID,
			AnalysisID:       rec.AnalysisID,
			UserID:           s.userID,
			Username:         s.username,
			Role:             s.role,
			Tier:             s.tier,
			StatusJWT:        s.statusJWT,
			AuthToken:        s.authToken,
			TradingStyle:     constants.TradingStyle(rec.TradingStyle),
			Grade:            rec.Grade,
			Session:          rec.Session,
			SetupType:        rec.SetupType,
			ExecutionMode:    rec.ExecutionMode,
			ConfluenceScore:  rec.ConfluenceScore,
			EntryPrice:       rec.EntryPrice,
			StopLoss:         rec.StopLoss,
			InitialSL:        rec.InitialSL,
			Point:            rec.Point,
			Digits:           rec.Digits,
			TP1Price:         rec.TP1Price,
			TP1Pct:           rec.TP1Pct,
			TP2Price:         rec.TP2Price,
			TP2Pct:           rec.TP2Pct,
			TP3Price:         rec.TP3Price,
			TP3Pct:           rec.TP3Pct,
			TotalLotSize:     rec.TotalLotSize,
			RemainingLotSize: rec.RemainingLotSize,
			RiskAmount:       rec.RiskAmount,
			RiskPercent:      rec.RiskPercent,
			RRRatio:          rec.RRRatio,
			Slippage:         rec.Slippage,
			Status:           constants.TradeStatus(rec.Status),
			BreakevenSet:     rec.BreakevenSet,
			TP1Hit:           rec.TP1Hit,
			TP2Hit:           rec.TP2Hit,
			TP3Hit:           rec.TP3Hit,
			// Preserve the recovered row's provenance: a system trade that
			// was merely re-adopted by the reconciler stays SYSTEM.
			Origin:           rec.Origin,
			OpenedAt:         rec.OpenedAt,
		}, nil
	}

	// 2) Genuinely manual / external position: safe POSITIONAL import.
	s.log.Info().
		Str("ticket", pos.Ticket).
		Str("symbol", pos.Symbol).
		Str("style", string(constants.StyleManualDefault)).
		Msg("discovered_manual_position_importing_as_positional")

	trade := &types.Trade{
		TradeID:          GenerateTradeID(),
		Symbol:           pos.Symbol,
		Direction:        constants.Direction(pos.Direction),
		BrokerOrderID:    pos.Ticket,
		UserID:           s.userID,
		Username:         s.username,
		Role:             s.role,
		Tier:             s.tier,
		StatusJWT:        s.statusJWT,
		AuthToken:        s.authToken,
		TradingStyle:     constants.StyleManualDefault,
		Grade:            "MANUAL/RECONCILED",
		Origin:           journal.OriginManualReconciled,
		EntryPrice:       pos.EntryPrice,
		StopLoss:         pos.StopLoss,
		InitialSL:        pos.StopLoss,
		TP1Price:         pos.TakeProfit,
		RRRatio:          plannedRR(pos.EntryPrice, pos.StopLoss, pos.TakeProfit),
		TotalLotSize:     pos.Volume,
		RemainingLotSize: pos.Volume,
		Status:           constants.StatusActive,
		OpenedAt:         time.Now().UTC(),
	}

	dbRecord := &journal.TradeRecord{
		UserID:           trade.UserID,
		TradeID:          trade.TradeID,
		Symbol:           trade.Symbol,
		Direction:        string(trade.Direction),
		BrokerOrderID:    trade.BrokerOrderID,
		TradingStyle:     string(trade.TradingStyle),
		Grade:            trade.Grade,
		Origin:           trade.Origin,
		EntryPrice:       trade.EntryPrice,
		StopLoss:         trade.StopLoss,
		InitialSL:        trade.InitialSL,
		TP1Price:         trade.TP1Price,
		RRRatio:          trade.RRRatio,
		TotalLotSize:     trade.TotalLotSize,
		RemainingLotSize: trade.RemainingLotSize,
		Status:           string(trade.Status),
		OpenedAt:         trade.OpenedAt,
	}

	if err := s.repo.InsertTrade(ctx, dbRecord); err != nil {
		return nil, err
	}

	return trade, nil
}

// plannedRR computes the planned reward:risk of a manually-opened
// position from its broker entry, stop-loss and take-profit:
//
//	RR = |tp - entry| / |entry - sl|
//
// It returns 0 (RR unknown -> the journal cell stays blank) when the
// stop-loss or take-profit is absent, or when the risk distance is
// non-positive. We never fabricate a ratio for a manual trade that did
// not set both a stop and a target.
func plannedRR(entry, sl, tp float64) float64 {
	if entry <= 0 || sl <= 0 || tp <= 0 {
		return 0
	}
	risk := math.Abs(entry - sl)
	if risk <= 0 {
		return 0
	}
	reward := math.Abs(tp - entry)
	if reward <= 0 {
		return 0
	}
	return reward / risk
}
