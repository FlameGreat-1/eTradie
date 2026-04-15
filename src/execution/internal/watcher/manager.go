package watcher

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
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

// WatcherPersistence is the interface for persisting watchers to survive
// service restarts. Implemented by store.WatcherStore.
type WatcherPersistence interface {
	Insert(ctx context.Context, order *models.Order) error
	Delete(ctx context.Context, watcherID string) error
}

// Manager tracks all active instant-mode watchers. Thread-safe.
// Provides Arm/Disarm lifecycle and coordinates graceful shutdown.
type Manager struct {
	broker    broker.Port
	gateway   GatewayPort
	audit     *audit.Logger
	transport *alertredis.Transport
	store     WatcherPersistence
	tickCache *TickCache
	cfg       Config
	log       zerolog.Logger

	mu           sync.RWMutex
	watchers     map[string]*Watcher // key: order.WatcherID
	shuttingDown bool
	ctx          context.Context
	cancel       context.CancelFunc
}

// NewManager creates a watcher manager. The provided context controls
// the lifecycle of all spawned watchers — cancelling it stops all.
// The store parameter is optional (nil-safe) for backward compatibility
// with tests that don't need persistence.
func NewManager(
	bp broker.Port,
	gw GatewayPort,
	al *audit.Logger,
	transport *alertredis.Transport,
	cfg Config,
	persistence WatcherPersistence,
) *Manager {
	ctx, cancel := context.WithCancel(context.Background())
	return &Manager{
		broker:    bp,
		gateway:   gw,
		audit:     al,
		transport: transport,
		store:     persistence,
		tickCache: NewTickCache(bp, cfg.PollIntervalMs),
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

	if m.shuttingDown {
		m.log.Warn().
			Str("watcher_id", order.WatcherID).
			Str("symbol", order.Symbol).
			Msg("manager_shutting_down_cannot_arm")
		return
	}

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
		tickCache: m.tickCache,
		cfg:       m.cfg,
		log: m.log.With().
			Str("watcher_id", order.WatcherID).
			Str("symbol", order.Symbol).
			Str("analysis_id", order.AnalysisID).
			Logger(),
		done: make(chan struct{}),
	}

	m.watchers[order.WatcherID] = w

	// Subscribe to tick cache for this symbol.
	m.tickCache.Subscribe(order.Symbol)

	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "armed").Inc()

	go w.run(m.ctx, m.onWatcherDone)

	// Persist the watcher to DB so it survives service restarts.
	// Fire-and-forget: errors are logged but don't block the watcher.
	if m.store != nil {
		if err := m.store.Insert(context.Background(), order); err != nil {
			m.log.Error().Err(err).Str("watcher_id", order.WatcherID).Msg("watcher_persist_failed")
		}
	}

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
		m.tickCache.Unsubscribe(w.order.Symbol)
		// Remove persistence record.
		if m.store != nil {
			if err := m.store.Delete(context.Background(), watcherID); err != nil {
				m.log.Error().Err(err).Str("watcher_id", watcherID).Msg("watcher_persist_delete_on_disarm_failed")
			}
		}
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
	m.mu.Lock()
	m.shuttingDown = true
	m.mu.Unlock()

	m.log.Info().Int("active_watchers", m.ActiveCount()).Msg("watcher_manager_shutting_down")
	m.tickCache.Shutdown()
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
// the watcher from the active map and deletes the persistence record.
// Thread-safe.
func (m *Manager) onWatcherDone(watcherID string) {
	m.mu.Lock()
	var symbol string
	if w, ok := m.watchers[watcherID]; ok {
		symbol = w.order.Symbol
	}
	delete(m.watchers, watcherID)
	m.mu.Unlock()

	if symbol != "" {
		m.tickCache.Unsubscribe(symbol)
	}

	// Remove persistence record (order filled, timed out, or disarmed).
	if m.store != nil {
		if err := m.store.Delete(context.Background(), watcherID); err != nil {
			m.log.Error().Err(err).Str("watcher_id", watcherID).Msg("watcher_persist_delete_failed")
		}
	}
}

// RefreshUserOrderTokens updates the AuthToken on all active watchers
// owned by the given user. Called when the user makes any authenticated
// request so that watchers can make authenticated broker calls even
// after the original session token expires.
//
// This is critical because the watcher timeout (default 45 min) can
// exceed the access token TTL (default 15 min). Without token refresh,
// broker calls fail with 401 after the token expires, causing missed
// trade entries on valid setups.
func (m *Manager) RefreshUserOrderTokens(userID, newToken string) int {
	if userID == "" || newToken == "" {
		return 0
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	refreshed := 0
	for _, w := range m.watchers {
		w.order.RLock()
		ownerMatch := w.order.UserID == userID
		currentToken := w.order.AuthToken
		w.order.RUnlock()

		if ownerMatch && currentToken != newToken {
			w.order.Lock()
			w.order.AuthToken = newToken
			w.order.Unlock()
			refreshed++
		}
	}

	if refreshed > 0 {
		m.log.Info().
			Str("user_id", userID).
			Int("watchers_refreshed", refreshed).
			Msg("watcher_auth_tokens_refreshed")
	}

	return refreshed
}

// TickCache returns the shared tick price cache. Exposed so that
// main.go can set the auth token on startup.
func (m *Manager) TickCache() *TickCache {
	return m.tickCache
}

// Watcher monitors a single instant-mode order's entry zone, calls
// the Gateway for LTF confirmation when price enters the zone, and
// fires the market order upon confirmation. Runs as a single goroutine.
type Watcher struct {
	order          *models.Order
	broker         broker.Port
	gateway        GatewayPort
	audit          *audit.Logger
	transport      *alertredis.Transport
	tickCache      *TickCache
	cfg            Config
	timeoutMinutes int // Resolved style-specific timeout (set in run())
	log            zerolog.Logger
	done           chan struct{}
	stopOnce       sync.Once
}

func (w *Watcher) stop() {
	w.stopOnce.Do(func() {
		close(w.done)
	})
}

func (w *Watcher) run(parentCtx context.Context, onDone func(string)) {
	defer onDone(w.order.WatcherID)

	// Resolve timeout. If TimeoutOverride is set (restored watcher),
	// use the remaining duration so the watcher expires at the correct
	// absolute time. Otherwise, resolve from the trading style map.
	var timeout time.Duration
	if w.order.TimeoutOverride > 0 {
		timeout = w.order.TimeoutOverride
		w.timeoutMinutes = int(timeout.Minutes())
	} else {
		w.timeoutMinutes = constants.WatcherTimeoutForStyle(w.order.TradingStyle, w.cfg.TimeoutMinutes)
		timeout = time.Duration(w.timeoutMinutes) * time.Minute
	}
	ctx, cancel := context.WithTimeout(parentCtx, timeout)
	defer cancel()

	pollInterval := time.Duration(w.cfg.PollIntervalMs) * time.Millisecond
	if pollInterval <= 0 {
		pollInterval = 100 * time.Millisecond // Default fallback
	}
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
		w.order.RLock()
		token := w.order.AuthToken
		w.order.RUnlock()
		authCtx := auth.InjectTokenIntoContext(ctx, token)
		w.fireMarketOrder(authCtx)
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
			// Build a fresh auth context on every tick cycle using the
			// order's current AuthToken. The token may be refreshed by
			// RefreshUserOrderTokens (user login or service token renewal).
			// The watcher timeout (default 45 min) can exceed the access
			// token TTL (default 15 min), so we must always use the
			// latest token to avoid 401 errors on broker calls.
			w.order.RLock()
			currentToken := w.order.AuthToken
			w.order.RUnlock()
			authCtx := auth.InjectTokenIntoContext(ctx, currentToken)

			if w.checkAndExecute(authCtx) {
				return
			}
		}
	}
}

// checkAndExecute polls the tick price, checks if it's in the entry
// zone, and if so, triggers the confirmation + execution flow.
// Returns true if the watcher should stop (order placed or fatal error).
func (w *Watcher) checkAndExecute(ctx context.Context) bool {
	// Read tick price from the shared cache. The cache is populated
	// by a single poller per symbol, eliminating redundant HTTP calls.
	tick := w.tickCache.GetTickPrice(w.order.Symbol)
	if tick == nil {
		// Cache not yet populated. Skip this cycle.
		return false
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
	if tick == nil {
		return false
	}
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
	if confirmInterval <= 0 {
		confirmInterval = 1 * time.Second // Default fallback
	}
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
	// Pass structural parameters for the lightweight LTF confirmation path.
	// This allows the Gateway to call /internal/ta/confirm_ltf instead of
	// re-running the full TA pipeline (~100ms vs ~5s).
	var params *ConfirmSetupParams
	if w.order.OBUpper > 0 && w.order.OBLower > 0 {
		dir := "BULLISH"
		if w.order.Direction == "SHORT" {
			dir = "BEARISH"
		}
		params = &ConfirmSetupParams{
			OBUpper:      w.order.OBUpper,
			OBLower:      w.order.OBLower,
			LTFTimeframe: w.order.LTFTimeframe,
			Direction:    dir,
			EntryPrice:   w.order.EntryPrice,
		}
	}

	var result *ConfirmResult
	var err error
	if gwWithParams, ok := w.gateway.(*GatewayGRPCClient); ok && params != nil {
		result, err = gwWithParams.ConfirmSetupWithParams(
			ctx, w.order.Symbol, w.order.AnalysisID, w.order.AnalysisID, params,
		)
	} else {
		result, err = w.gateway.ConfirmSetup(
			ctx, w.order.Symbol, w.order.AnalysisID, w.order.AnalysisID,
		)
	}
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

		if w.transport != nil {
			w.transport.Publish(ctx,
				alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityCritical,
					fmt.Sprintf("CRITICAL: Market order FAILED for %s: %s", w.order.Symbol, err.Error())).
					WithUserID(w.order.UserID).
					WithSymbol(w.order.Symbol).
					WithDirection(string(w.order.Direction)).
					WithDetail("watcher_id", w.order.WatcherID).
					WithDetail("analysis_id", w.order.AnalysisID).
					WithDetail("error", err.Error()),
			)
		}
		return true // Stop watcher — do NOT retry market orders.
	}

	if result.Status == "REJECTED" {
		w.log.Error().
			Str("reason", result.ErrorMessage).
			Msg("watcher_market_order_rejected")

		if w.transport != nil {
			w.transport.Publish(ctx,
				alert.NewEvent(alert.SourceExecution, alert.TypeOrderRejected, alert.SeverityCritical,
					fmt.Sprintf("Market order REJECTED for %s: %s", w.order.Symbol, result.ErrorMessage)).
					WithUserID(w.order.UserID).
					WithSymbol(w.order.Symbol).
					WithDirection(string(w.order.Direction)).
					WithDetail("watcher_id", w.order.WatcherID),
			)
		}
		return true
	}

	// SUCCESS — order filled.
	w.order.Lock()
	w.order.BrokerOrderID = result.BrokerOrderID
	w.order.Unlock()

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

	if w.transport != nil {
		w.transport.Publish(ctx,
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderPlaced, alert.SeverityInfo,
				fmt.Sprintf("Instant market order FILLED for %s at %.5f", w.order.Symbol, result.FillPrice)).
				WithUserID(w.order.UserID).
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
	}

	return true
}

func (w *Watcher) handleTimeout() {
	w.log.Warn().
		Int("timeout_minutes", w.timeoutMinutes).
		Str("trading_style", string(w.order.TradingStyle)).
		Msg("watcher_timed_out")

	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "timeout").Inc()

	if w.transport != nil {
		w.transport.Publish(context.Background(),
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderExpired, alert.SeverityWarning,
				fmt.Sprintf("Instant watcher timed out for %s after %d minutes (%s style)",
					w.order.Symbol, w.timeoutMinutes, w.order.TradingStyle)).
				WithUserID(w.order.UserID).
				WithSymbol(w.order.Symbol).
				WithDirection(string(w.order.Direction)).
				WithDetails(map[string]interface{}{
					"watcher_id":      w.order.WatcherID,
					"analysis_id":     w.order.AnalysisID,
					"entry_price":     w.order.EntryPrice,
					"timeout_minutes": w.timeoutMinutes,
					"trading_style":   string(w.order.TradingStyle),
				}),
		)
	}
}
