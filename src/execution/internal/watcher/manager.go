package watcher

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/execution/internal/audit"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// GatewayPort is the interface Execution uses to call back to the
// Gateway for TA confirmation pulses. This follows Dependency Inversion:
// the watcher depends on this abstraction, not on Gateway internals.
type GatewayPort interface {
	ConfirmSetup(ctx context.Context, symbol, analysisID, traceID string) (*ConfirmResult, error)
	NotifyExecutionCompleted(ctx context.Context, order *models.Order, brokerOrderID string, fillPrice, slippage float64) error
}

// ConfirmResult holds the Gateway's response to a confirmation pulse.
type ConfirmResult struct {
	Confirmed       bool
	LTFConfirmation bool
	Reason          string
}

// Config holds watcher-specific configuration passed from the
// execution config at startup. Immutable after creation.
type Config struct {
	PollIntervalMs          int
	TimeoutMinutes          int
	ConfirmPollIntervalSecs int
}

// Manager tracks all active instant-mode watchers. Thread-safe.
// Provides Arm/Disarm lifecycle and coordinates graceful shutdown.
type Manager struct {
	broker    broker.Port
	gateway   GatewayPort
	audit     *audit.Logger
	transport *alertredis.Transport
	cfg       Config
	log       zerolog.Logger

	mu       sync.RWMutex
	watchers map[string]*Watcher // key: order.WatcherID
	ctx      context.Context
	cancel   context.CancelFunc
}

// NewManager creates a watcher manager. The provided context controls
// the lifecycle of all spawned watchers — cancelling it stops all.
func NewManager(
	bp broker.Port,
	gw GatewayPort,
	al *audit.Logger,
	transport *alertredis.Transport,
	cfg Config,
) *Manager {
	ctx, cancel := context.WithCancel(context.Background())
	return &Manager{
		broker:    bp,
		gateway:   gw,
		audit:     al,
		transport: transport,
		cfg:       cfg,
		log:       observability.Logger("watcher_manager"),
		watchers:  make(map[string]*Watcher),
		ctx:       ctx,
		cancel:    cancel,
	}
}

// Arm spawns a background watcher goroutine for an instant-mode order.
// Returns immediately. The watcher monitors tick prices and executes
// the full confirmation + market order flow autonomously.
func (m *Manager) Arm(order *models.Order) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.watchers[order.WatcherID]; exists {
		m.log.Warn().
			Str("watcher_id", order.WatcherID).
			Str("symbol", order.Symbol).
			Msg("watcher_already_exists_skipping")
		return
	}

	w := &Watcher{
		order:     order,
		broker:    m.broker,
		gateway:   m.gateway,
		audit:     m.audit,
		transport: m.transport,
		cfg:       m.cfg,
		log: m.log.With().
			Str("watcher_id", order.WatcherID).
			Str("symbol", order.Symbol).
			Str("analysis_id", order.AnalysisID).
			Logger(),
		done: make(chan struct{}),
	}

	m.watchers[order.WatcherID] = w

	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "armed").Inc()

	go w.run(m.ctx, m.onWatcherDone)

	m.log.Info().
		Str("watcher_id", order.WatcherID).
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Float64("entry_price", order.EntryPrice).
		Float64("overshoot_tolerance", order.OvershootTolerance).
		Int("timeout_minutes", m.cfg.TimeoutMinutes).
		Int("poll_interval_ms", m.cfg.PollIntervalMs).
		Msg("watcher_armed")
}

// Disarm cancels and removes a watcher by its ID.
func (m *Manager) Disarm(watcherID string) {
	m.mu.Lock()
	w, exists := m.watchers[watcherID]
	if exists {
		delete(m.watchers, watcherID)
	}
	m.mu.Unlock()

	if exists {
		w.stop()
		m.log.Info().Str("watcher_id", watcherID).Msg("watcher_disarmed")
	}
}

// ActiveCount returns the number of currently active watchers.
func (m *Manager) ActiveCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.watchers)
}

// Shutdown cancels all active watchers and waits for them to finish.
// Must be called during service shutdown to prevent goroutine leaks.
func (m *Manager) Shutdown() {
	m.log.Info().Int("active_watchers", m.ActiveCount()).Msg("watcher_manager_shutting_down")
	m.cancel()

	// Wait for all watchers to finish with a deadline.
	deadline := time.After(10 * time.Second)
	for {
		if m.ActiveCount() == 0 {
			break
		}
		select {
		case <-deadline:
			m.log.Warn().
				Int("remaining", m.ActiveCount()).
				Msg("watcher_shutdown_deadline_exceeded")
			return
		case <-time.After(100 * time.Millisecond):
			// Check again.
		}
	}
	m.log.Info().Msg("watcher_manager_shutdown_complete")
}

// onWatcherDone is a callback invoked when a watcher finishes. Removes
// the watcher from the active map. Thread-safe.
func (m *Manager) onWatcherDone(watcherID string) {
	m.mu.Lock()
	delete(m.watchers, watcherID)
	m.mu.Unlock()
}

// Watcher monitors a single instant-mode order's entry zone, calls
// the Gateway for LTF confirmation when price enters the zone, and
// fires the market order upon confirmation. Runs as a single goroutine.
type Watcher struct {
	order     *models.Order
	broker    broker.Port
	gateway   GatewayPort
	audit     *audit.Logger
	transport *alertredis.Transport
	cfg       Config
	log       zerolog.Logger
	done      chan struct{}
	stopOnce  sync.Once
}

func (w *Watcher) stop() {
	w.stopOnce.Do(func() {
		close(w.done)
	})
}

func (w *Watcher) run(parentCtx context.Context, onDone func(string)) {
	defer onDone(w.order.WatcherID)

	timeout := time.Duration(w.cfg.TimeoutMinutes) * time.Minute
	ctx, cancel := context.WithTimeout(parentCtx, timeout)
	defer cancel()

	pollInterval := time.Duration(w.cfg.PollIntervalMs) * time.Millisecond
	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	w.log.Info().
		Float64("entry_price", w.order.EntryPrice).
		Float64("stop_loss", w.order.StopLoss).
		Float64("overshoot", w.order.OvershootTolerance).
		Dur("timeout", timeout).
		Bool("pre_confirmed", w.order.LTFConfirmed).
		Msg("watcher_monitoring_started")

	// Pre-confirmed fast path: if Gateway already saw LTF confirmation at analysis time,
	// we skip the waiting/polling loop and fire the market order immediately.
	if w.order.LTFConfirmed {
		w.log.Info().Msg("watcher_pre_confirmed_firing_market_order_immediately")
		w.fireMarketOrder(ctx)
		return
	}

	for {
		select {
		case <-ctx.Done():
			w.handleTimeout()
			return
		case <-w.done:
			w.log.Info().Msg("watcher_disarmed_externally")
			return
		case <-ticker.C:
			if w.checkAndExecute(ctx) {
				return
			}
		}
	}
}

// checkAndExecute polls the tick price, checks if it's in the entry
// zone, and if so, triggers the confirmation + execution flow.
// Returns true if the watcher should stop (order placed or fatal error).
func (w *Watcher) checkAndExecute(ctx context.Context) bool {
	tick, err := w.broker.GetTickPrice(ctx, w.order.Symbol)
	if err != nil {
		w.log.Warn().Err(err).Msg("watcher_tick_fetch_failed")
		return false // Transient error, keep polling.
	}

	if !w.isPriceInZone(tick) {
		return false
	}

	w.log.Info().
		Float64("bid", tick.Bid).
		Float64("ask", tick.Ask).
		Float64("entry_price", w.order.EntryPrice).
		Msg("watcher_price_in_zone_triggering_confirmation")

	// Price is in the entry zone. Begin confirmation loop.
	return w.confirmAndExecute(ctx)
}

// isPriceInZone checks if the current tick price is within the order's
// entry zone, accounting for direction and overshoot tolerance.
func (w *Watcher) isPriceInZone(tick *models.TickPrice) bool {
	tolerance := w.order.OvershootTolerance
	entry := w.order.EntryPrice

	switch w.order.Direction {
	case constants.DirectionLong:
		// For LONG: we buy at the Ask. Entry zone is at/below entry + tolerance.
		return tick.Ask <= entry+tolerance
	case constants.DirectionShort:
		// For SHORT: we sell at the Bid. Entry zone is at/above entry - tolerance.
		return tick.Bid >= entry-tolerance
	default:
		return false
	}
}

// confirmAndExecute calls the Gateway's ConfirmSetup RPC. If confirmed,
// fires the market order. If not confirmed, enters a polling loop (every
// ConfirmPollIntervalSecs) until confirmed or timeout.
func (w *Watcher) confirmAndExecute(ctx context.Context) bool {
	confirmInterval := time.Duration(w.cfg.ConfirmPollIntervalSecs) * time.Second
	confirmTicker := time.NewTicker(confirmInterval)
	defer confirmTicker.Stop()

	// First attempt immediately.
	if w.tryConfirmAndFire(ctx) {
		return true
	}

	for {
		select {
		case <-ctx.Done():
			w.handleTimeout()
			return true
		case <-w.done:
			w.log.Info().Msg("watcher_disarmed_during_confirmation")
			return true
		case <-confirmTicker.C:
			if w.tryConfirmAndFire(ctx) {
				return true
			}
		}
	}
}

// tryConfirmAndFire makes a single ConfirmSetup call and, if confirmed,
// fires the market order. Returns true if the watcher should stop.
func (w *Watcher) tryConfirmAndFire(ctx context.Context) bool {
	result, err := w.gateway.ConfirmSetup(ctx, w.order.Symbol, w.order.AnalysisID, w.order.AnalysisID)
	if err != nil {
		w.log.Warn().Err(err).Msg("watcher_confirm_call_failed")
		return false // Transient error, retry on next tick.
	}

	if !result.Confirmed {
		w.log.Info().
			Str("reason", result.Reason).
			Msg("watcher_ltf_not_confirmed_retrying")
		return false
	}

	// LTF confirmed! Fire the market order.
	w.log.Info().
		Str("reason", result.Reason).
		Msg("watcher_ltf_confirmed_firing_market_order")

	return w.fireMarketOrder(ctx)
}

// fireMarketOrder places the market order at the broker. This is the
// final, irreversible step. Any error here is critical.
func (w *Watcher) fireMarketOrder(ctx context.Context) bool {
	placement := &models.OrderPlacement{
		Symbol:     w.order.Symbol,
		Direction:  constants.BrokerDirection(w.order.Direction),
		OrderType:  string(constants.BrokerOrderMarket),
		Price:      0, // Market order — broker fills at best available.
		StopLoss:   w.order.StopLoss,
		TakeProfit: w.order.TP1Price,
		LotSize:    w.order.LotSize,
		Comment:    w.order.AnalysisID,
	}

	result, err := w.broker.PlaceMarketOrder(ctx, placement)
	if err != nil {
		w.log.Error().Err(err).Msg("watcher_market_order_failed")

		w.transport.Publish(ctx,
			alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityCritical,
				fmt.Sprintf("CRITICAL: Market order FAILED for %s: %s", w.order.Symbol, err.Error())).
				WithSymbol(w.order.Symbol).
				WithDirection(string(w.order.Direction)).
				WithDetail("watcher_id", w.order.WatcherID).
				WithDetail("analysis_id", w.order.AnalysisID).
				WithDetail("error", err.Error()),
		)
		return true // Stop watcher — do NOT retry market orders.
	}

	if result.Status == "REJECTED" {
		w.log.Error().
			Str("reason", result.ErrorMessage).
			Msg("watcher_market_order_rejected")

		w.transport.Publish(ctx,
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderRejected, alert.SeverityCritical,
				fmt.Sprintf("Market order REJECTED for %s: %s", w.order.Symbol, result.ErrorMessage)).
				WithSymbol(w.order.Symbol).
				WithDirection(string(w.order.Direction)).
				WithDetail("watcher_id", w.order.WatcherID),
		)
		return true
	}

	// SUCCESS — order filled.
	w.order.BrokerOrderID = result.BrokerOrderID

	w.log.Info().
		Str("broker_order_id", result.BrokerOrderID).
		Float64("fill_price", result.FillPrice).
		Float64("slippage", result.Slippage).
		Float64("lot_size", w.order.LotSize).
		Msg("watcher_market_order_filled")

	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "filled").Inc()

	// Notify Gateway immediately to complete the Execution phase and hand off to Module C.
	if err := w.gateway.NotifyExecutionCompleted(ctx, w.order, result.BrokerOrderID, result.FillPrice, result.Slippage); err != nil {
		w.log.Error().Err(err).Msg("failed_to_notify_gateway_of_execution_completion")
		// We log the error but do not fail the execution, as the order is already placed.
		// Alerting can catch this for manual reconciliation if needed.
	}

	// Audit the fill.
	w.audit.LogOrderPlaced(ctx, w.order)

	w.transport.Publish(ctx,
		alert.NewEvent(alert.SourceExecution, alert.TypeOrderPlaced, alert.SeverityInfo,
			fmt.Sprintf("Instant market order FILLED for %s at %.5f", w.order.Symbol, result.FillPrice)).
			WithSymbol(w.order.Symbol).
			WithDirection(string(w.order.Direction)).
			WithDetails(map[string]interface{}{
				"order_id":        w.order.OrderID,
				"broker_order_id": result.BrokerOrderID,
				"fill_price":      result.FillPrice,
				"slippage":        result.Slippage,
				"lot_size":        w.order.LotSize,
				"watcher_id":      w.order.WatcherID,
				"analysis_id":     w.order.AnalysisID,
			}),
	)

	return true
}

func (w *Watcher) handleTimeout() {
	w.log.Warn().
		Int("timeout_minutes", w.cfg.TimeoutMinutes).
		Msg("watcher_timed_out")

	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "timeout").Inc()

	w.transport.Publish(context.Background(),
		alert.NewEvent(alert.SourceExecution, alert.TypeOrderExpired, alert.SeverityWarning,
			fmt.Sprintf("Instant watcher timed out for %s after %d minutes",
				w.order.Symbol, w.cfg.TimeoutMinutes)).
			WithSymbol(w.order.Symbol).
			WithDirection(string(w.order.Direction)).
			WithDetails(map[string]interface{}{
				"watcher_id":      w.order.WatcherID,
				"analysis_id":     w.order.AnalysisID,
				"entry_price":     w.order.EntryPrice,
				"timeout_minutes": w.cfg.TimeoutMinutes,
			}),
	)
}
