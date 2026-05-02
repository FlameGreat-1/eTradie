package monitoring

import (
	"context"
	"errors"
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

// StateReconciler is responsible for ensuring the Management engine's internal
// memory exactly matches the MT5 broker's reality. It performs a startup sync
// and listens to real-time websocket updates.
type StateReconciler struct {
	mgr       *Manager
	bp        broker.Port
	repo      *journal.Repository
	transport AlertTransport
	userID    string
	authToken string
	log       zerolog.Logger
}

// NewStateReconciler creates a reconciler for a specific user.
func NewStateReconciler(
	mgr *Manager,
	bp broker.Port,
	repo *journal.Repository,
	transport AlertTransport,
	userID, authToken string,
) *StateReconciler {
	return &StateReconciler{
		mgr:       mgr,
		bp:        bp,
		repo:      repo,
		transport: transport,
		userID:    userID,
		authToken: authToken,
		log:       observability.Logger("state_reconciler").With().Str("user_id", userID).Logger(),
	}
}

// RunStartupSync fetches all currently open MT5 positions for this user.
// If it finds a position that is not in the database, it imports it.
func (s *StateReconciler) RunStartupSync(ctx context.Context) error {
	s.log.Info().Msg("starting_startup_sync_for_user")

	tradeCtx := auth.InjectTokenIntoContext(ctx, s.authToken)

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

		s.log.Info().Str("ticket", pos.Ticket).Str("symbol", pos.Symbol).Msg("discovered_orphaned_position_importing")

		// Construct a Trade from the raw position.
		trade := &types.Trade{
			TradeID:          GenerateTradeID(),
			Symbol:           pos.Symbol,
			Direction:        constants.Direction(pos.Direction),
			BrokerOrderID:    pos.Ticket,
			UserID:           s.userID,
			AuthToken:        s.authToken,
			TradingStyle:     constants.StyleIntraday, // Default fallback
			Grade:            "MANUAL/RECONCILED",
			EntryPrice:       pos.EntryPrice,
			StopLoss:         pos.StopLoss,
			InitialSL:        pos.StopLoss,
			TP1Price:         pos.TakeProfit,
			TotalLotSize:     pos.Volume,
			RemainingLotSize: pos.Volume,
			Status:           constants.StatusActive,
			OpenedAt:         time.Now().UTC(),
		}

		// Insert into PostgreSQL.
		dbRecord := &journal.TradeRecord{
			UserID:           trade.UserID,
			TradeID:          trade.TradeID,
			Symbol:           trade.Symbol,
			Direction:        string(trade.Direction),
			BrokerOrderID:    trade.BrokerOrderID,
			TradingStyle:     string(trade.TradingStyle),
			Grade:            trade.Grade,
			EntryPrice:       trade.EntryPrice,
			StopLoss:         trade.StopLoss,
			InitialSL:        trade.InitialSL,
			TP1Price:         trade.TP1Price,
			TotalLotSize:     trade.TotalLotSize,
			Status:           string(trade.Status),
			OpenedAt:         trade.OpenedAt,
		}

		if err := s.repo.InsertTrade(ctx, dbRecord); err != nil {
			s.log.Error().Err(err).Str("ticket", pos.Ticket).Msg("failed_to_insert_reconciled_trade")
			continue
		}

		// Register with the manager so it gets actively monitored.
		s.mgr.RegisterTrade(trade)
		imported++
	}

	s.log.Info().Int("imported_trades", imported).Msg("startup_sync_complete_for_active_positions")

	// ---- Phase 2: History Sync ----
	// Fetch last 30 days of closed deals to rebuild the Journal if wiped
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

// RunStreamListener opens the WebSocket to the Python engine and listens
// for real-time changes to the MT5 positions (e.g. user manually drags SL).
//
// Uses exponential backoff when the Engine returns ErrNoBrokerConfigured
// (close code 4004), capping at maxBackoff. The backoff resets to the
// base interval on any successful data frame, so a user who configures
// their broker connection later will resume fast polling immediately.
func (s *StateReconciler) RunStreamListener(ctx context.Context) {
	s.log.Info().Msg("starting_position_stream_listener")

	const baseBackoff = 2 * time.Second
	const maxBackoff = 5 * time.Minute
	backoff := baseBackoff

	// Retry loop for websocket connection
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		tradeCtx := auth.InjectTokenIntoContext(ctx, s.authToken)

		ch := make(chan []broker.PositionInfo, 10)
		errCh := make(chan error, 1)

		go func() {
			err := s.bp.StreamPositions(tradeCtx, ch)
			errCh <- err
			close(ch)
		}()

		// Process stream
		for positions := range ch {
			s.processPositionUpdate(tradeCtx, positions)
			// Reset backoff on successful data flow.
			backoff = baseBackoff
		}

		// Retrieve the stream error. The channel is buffered (cap 1)
		// and always receives a value before close(ch), so this is
		// guaranteed to not block after the range loop exits.
		streamErr := <-errCh

		if streamErr != nil {
			if errors.Is(streamErr, broker.ErrNoBrokerConfigured) {
				// User has no broker connection configured. Exponential
				// backoff avoids hammering the Engine with futile
				// connect/auth/close cycles every 5 seconds.
				s.log.Info().
					Dur("backoff", backoff).
					Msg("no_broker_configured_backing_off")
			} else {
				// Transient network error or unexpected disconnect.
				// Log at Warn and retry with the current backoff.
				s.log.Warn().
					Err(streamErr).
					Dur("retry_in", backoff).
					Msg("position_stream_disconnected")
			}
		} else {
			s.log.Warn().
				Dur("retry_in", backoff).
				Msg("position_stream_ended_reconnecting")
		}

		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}

		// Grow backoff for repeated failures (capped at maxBackoff).
		// Resets to baseBackoff inside the data-processing loop above
		// when we receive at least one successful position frame.
		if backoff < maxBackoff {
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
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

		s.log.Info().Str("ticket", pos.Ticket).Str("symbol", pos.Symbol).Msg("discovered_new_position_in_stream_importing")

		trade := &types.Trade{
			TradeID:          GenerateTradeID(),
			Symbol:           pos.Symbol,
			Direction:        constants.Direction(pos.Direction),
			BrokerOrderID:    pos.Ticket,
			UserID:           s.userID,
			AuthToken:        s.authToken,
			TradingStyle:     constants.StyleIntraday,
			Grade:            "MANUAL/RECONCILED",
			EntryPrice:       pos.EntryPrice,
			StopLoss:         pos.StopLoss,
			InitialSL:        pos.StopLoss,
			TP1Price:         pos.TakeProfit,
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
			EntryPrice:       trade.EntryPrice,
			StopLoss:         trade.StopLoss,
			InitialSL:        trade.InitialSL,
			TP1Price:         trade.TP1Price,
			TotalLotSize:     trade.TotalLotSize,
			Status:           string(trade.Status),
			OpenedAt:         trade.OpenedAt,
		}

		if err := s.repo.InsertTrade(ctx, dbRecord); err != nil {
			s.log.Error().Err(err).Str("ticket", pos.Ticket).Msg("failed_to_insert_new_reconciled_trade")
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
