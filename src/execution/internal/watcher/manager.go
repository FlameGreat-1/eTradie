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
	ConfirmSetupWithParams(ctx context.Context, symbol, analysisID, traceID string, params *ConfirmSetupParams) (*ConfirmResult, error)
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

// WatcherUsage is the narrow contract the watcher manager needs from the
// billing usage store so the billing_usage.watcher_count column reflects
// reality. Pluggable for tests; main.go wires the real billing UsageStore
// via a small adapter so this package never imports billing/*.
type WatcherUsage interface {
	IncrementWatchers(ctx context.Context, userID string) error
	DecrementWatchers(ctx context.Context, userID string) error
}

// Manager tracks all active instant-mode watchers. Thread-safe.
// Provides Arm/Disarm lifecycle and coordinates graceful shutdown.
type Manager struct {
	broker    broker.Port
	gateway   GatewayPort
	audit     *audit.Logger
	transport *alertredis.Transport
	store     WatcherPersistence
	usage     WatcherUsage
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
// The persistence and usage parameters are optional (nil-safe) for
// backward compatibility with tests that don't need them.
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

// WithUsage attaches a billing-usage tracker so Arm/Disarm increments and
// decrements billing_usage.watcher_count for the affected user. Optional;
// nil keeps the manager fully functional but stops feeding the metric.
func (m *Manager) WithUsage(u WatcherUsage) *Manager {
	m.mu.Lock()
	m.usage = u
	m.mu.Unlock()
	return m
}

// trackArm fires a non-blocking watcher_count increment. Detached from the
// caller's context so a cancelled request does not abort the metric write,
// and run in a goroutine so the Arm hot path is never DB-bound.
func (m *Manager) trackArm(userID string) {
	if m.usage == nil || userID == "" {
		return
	}
	go func(uid string) {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if err := m.usage.IncrementWatchers(ctx, uid); err != nil {
			m.log.Warn().Err(err).Str("user_id", uid).Msg("watcher_usage_increment_failed")
		}
	}(userID)
}

func (m *Manager) trackDisarm(userID string) {
	if m.usage == nil || userID == "" {
		return
	}
	go func(uid string) {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if err := m.usage.DecrementWatchers(ctx, uid); err != nil {
			m.log.Warn().Err(err).Str("user_id", uid).Msg("watcher_usage_decrement_failed")
		}
	}(userID)
}

// Arm spawns a background watcher goroutine for an order.
// For INSTANT orders: monitors tick prices and executes the full
// confirmation + market order flow autonomously.
// For LIMIT orders: monitors the TTL timer and cancels the broker
// order when the timeout elapses.
// Returns immediately.
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

	modeLabel := string(order.ExecutionMode)

	// INSTANT orders need tick price monitoring; LIMIT orders only
	// need TTL enforcement (the broker handles the fill).
	if order.ExecutionMode == constants.ModeInstant {
		// Set this user's identity BEFORE subscribing so the first poll
		// for the (user, symbol) pair has a non-nil identity to
		// authenticate with. Pre-upgrade restored orders without
		// identity fields fall back to the parse-the-token shim.
		if order.UserID != "" {
			m.tickCache.SetServiceIdentity(&auth.Claims{
				UserID:   order.UserID,
				Username: order.Username,
				Role:     auth.Role(order.Role),
				Tier:     order.Tier,
				Status:   order.StatusJWT,
			}, order.AuthToken)
		} else if order.AuthToken != "" {
			m.tickCache.SetAuthToken(order.AuthToken)
		}

		// Subscribe the (user, symbol) pair. Each pair gets its own
		// dedicated poller running with that user's identity, so
		// multi-tenant correctness is preserved when two users hold
		// pending watchers on the same symbol but trade against
		// different brokers.
		m.tickCache.Subscribe(order.UserID, order.Symbol)
	}

	observability.OrderPlacementTotal.WithLabelValues(modeLabel, "armed").Inc()

	go w.run(m.ctx, m.onWatcherDone)

	// Persist the watcher to DB so it survives service restarts.
	// Fire-and-forget: errors are logged but don't block the watcher.
	if m.store != nil {
		if err := m.store.Insert(context.Background(), order); err != nil {
			m.log.Error().Err(err).Str("watcher_id", order.WatcherID).Msg("watcher_persist_failed")
		}
	}

	// Bump the user's billing_usage.watcher_count. Non-blocking, best-effort.
	m.trackArm(order.UserID)

	m.log.Info().
		Str("watcher_id", order.WatcherID).
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Str("execution_mode", modeLabel).
		Float64("entry_price", order.EntryPrice).
		Str("broker_order_id", order.BrokerOrderID).
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
		// Only unsubscribe from tick cache for INSTANT orders;
		// LIMIT orders never subscribed.
		if w.order.ExecutionMode == constants.ModeInstant {
			m.tickCache.Unsubscribe(w.order.UserID, w.order.Symbol)
		}
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
// the watcher from the active map, deletes the persistence record, and
// decrements the per-user billing_usage.watcher_count. Thread-safe.
func (m *Manager) onWatcherDone(watcherID string) {
	m.mu.Lock()
	var (
		symbol string
		mode   constants.ExecutionMode
		userID string
	)
	if w, ok := m.watchers[watcherID]; ok {
		symbol = w.order.Symbol
		mode = w.order.ExecutionMode
		userID = w.order.UserID
	}
	delete(m.watchers, watcherID)
	isShuttingDown := m.shuttingDown
	m.mu.Unlock()

	// Only unsubscribe from tick cache for INSTANT orders;
	// LIMIT orders never subscribed.
	if symbol != "" && mode == constants.ModeInstant {
		m.tickCache.Unsubscribe(userID, symbol)
	}

	// Remove persistence record (order filled, timed out, or disarmed).
	// If the manager is shutting down (e.g. service restart/rebuild), do NOT delete
	// the database record so it can be restored on startup.
	if !isShuttingDown && m.store != nil {
		if err := m.store.Delete(context.Background(), watcherID); err != nil {
			m.log.Error().Err(err).Str("watcher_id", watcherID).Msg("watcher_persist_delete_failed")
		}
	}

	// Decrement the user's billing_usage.watcher_count. Non-blocking.
	m.trackDisarm(userID)
}

// RefreshUserOrderIdentity updates the full identity (UserID is the
// matching key; Username, Role, Tier, StatusJWT, and AuthToken are
// the writable fields) on every active watcher owned by
// claims.UserID. Every field is overwritten atomically under the
// per-Order write lock so the watcher goroutine never observes a
// partial update.
//
// Called whenever the auth interceptor produced a fresh *auth.Claims.
func (m *Manager) RefreshUserOrderIdentity(claims *auth.Claims, newToken string) int {
	if claims == nil || claims.UserID == "" || newToken == "" {
		return 0
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	refreshed := 0
	for _, w := range m.watchers {
		w.order.RLock()
		ownerMatch := w.order.UserID == claims.UserID
		currentToken := w.order.AuthToken
		currentTier := w.order.Tier
		currentStatus := w.order.StatusJWT
		w.order.RUnlock()

		if !ownerMatch {
			continue
		}
		if currentToken == newToken && currentTier == claims.Tier && currentStatus == claims.Status {
			continue
		}

		w.order.Lock()
		w.order.Username = claims.Username
		w.order.Role = string(claims.Role)
		w.order.Tier = claims.Tier
		w.order.StatusJWT = claims.Status
		w.order.AuthToken = newToken
		w.order.Unlock()
		refreshed++
	}

	if refreshed > 0 {
		m.log.Info().
			Str("user_id", claims.UserID).
			Str("tier", claims.Tier).
			Str("status", claims.Status).
			Int("watchers_refreshed", refreshed).
			Msg("watcher_identity_refreshed")
	}

	return refreshed
}

// RefreshUserOrderTokens is the legacy entry point retained for the
// (rare) caller that has only a token. Parses the local-mint JWT and
// delegates to RefreshUserOrderIdentity. Returns 0 on parse failure or
// claim mismatch.
func (m *Manager) RefreshUserOrderTokens(userID, newToken string) int {
	if userID == "" || newToken == "" {
		return 0
	}
	claims := parseLocalServiceToken(newToken)
	if claims == nil || claims.UserID != userID {
		m.log.Warn().
			Str("expected_user_id", userID).
			Msg("watcher_token_refresh_skipped_claim_mismatch")
		return 0
	}
	return m.RefreshUserOrderIdentity(claims, newToken)
}

// TickCache returns the shared tick price cache. Exposed so that
// main.go can set the auth token on startup.
func (m *Manager) TickCache() *TickCache {
	return m.tickCache
}

// Watcher monitors a single order. For INSTANT orders, it polls tick
// prices, calls Gateway for LTF confirmation, and fires the market
// order. For LIMIT orders, it only enforces the TTL timeout and
// cancels the broker order when it expires. Runs as a single goroutine.
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

	w.log.Info().
		Str("execution_mode", string(w.order.ExecutionMode)).
		Float64("entry_price", w.order.EntryPrice).
		Float64("stop_loss", w.order.StopLoss).
		Dur("timeout", timeout).
		Str("broker_order_id", w.order.BrokerOrderID).
		Msg("watcher_monitoring_started")

	// LIMIT orders: the broker handles the fill. We only enforce the
	// TTL timeout. When the timeout fires, we cancel the broker order.
	if w.order.ExecutionMode == constants.ModeLimit {
		w.runLimitTTL(ctx)
		return
	}

	// INSTANT mode: full tick polling + LTF confirmation flow.
	w.runInstant(ctx)
}

// runLimitTTL is the run loop for LIMIT orders. It simply waits for
// the TTL timeout or external disarm, then cancels the broker order.
func (w *Watcher) runLimitTTL(ctx context.Context) {
	// Check every minute if the order was filled externally (e.g., by
	// the broker). If the order no longer exists at the broker, we can
	// stop early instead of waiting for the full TTL.
	checkInterval := 1 * time.Minute
	ticker := time.NewTicker(checkInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			// Only trigger timeout if the context completed due to the TTL deadline.
			// If context was cancelled due to service shutdown/restart, exit silently.
			if ctx.Err() == context.DeadlineExceeded {
				w.handleTimeout()
			}
			return
		case <-w.done:
			w.log.Info().Msg("limit_watcher_disarmed_externally")
			return
		case <-ticker.C:
			// Periodic liveness log so operators know the watcher is alive.
			w.log.Debug().
				Str("broker_order_id", w.order.BrokerOrderID).
				Msg("limit_watcher_ttl_check_alive")
		}
	}
}

// runInstant is the run loop for INSTANT orders. Polls tick prices,
// checks entry zone, calls Gateway for LTF confirmation, and fires
// the market order.
func (w *Watcher) runInstant(ctx context.Context) {
	pollInterval := time.Duration(w.cfg.PollIntervalMs) * time.Millisecond
	if pollInterval <= 0 {
		pollInterval = 100 * time.Millisecond // Default fallback
	}
	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	// Pre-confirmed fast path: if Gateway already saw LTF confirmation at analysis time,
	// we skip the waiting/polling loop and fire the market order immediately.
	if w.order.LTFConfirmed {
		w.log.Info().Msg("watcher_pre_confirmed_firing_market_order_immediately")
		// IdentityCtx injects claims AND token under one snapshot.
		w.order.RLock()
		authCtx := w.order.IdentityCtx(ctx)
		w.order.RUnlock()
		w.fireMarketOrder(authCtx)
		return
	}

	for {
		select {
		case <-ctx.Done():
			// Only trigger timeout if the context completed due to the TTL deadline.
			// If context was cancelled due to service shutdown/restart, exit silently.
			if ctx.Err() == context.DeadlineExceeded {
				w.handleTimeout()
			}
			return
		case <-w.done:
			w.log.Info().Msg("watcher_disarmed_externally")
			return
		case <-ticker.C:
			// Build a fresh auth context on every tick cycle from the
			// order's current identity + token. The token may be
			// refreshed by RefreshUserOrderTokens (user login or service
			// token renewal); since the watcher timeout (default 45m)
			// can exceed the access-token TTL (15m), the latest value
			// MUST be read every tick to avoid 401s.
			// IdentityCtx injects claims (resolves X-User-Id) AND token.
			w.order.RLock()
			authCtx := w.order.IdentityCtx(ctx)
			w.order.RUnlock()

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
	// Read tick price from the per-(user, symbol) cache. Each pair has
	// a dedicated poller authenticated with its owner's broker on the
	// engine side, so this lookup is always isolated to this user's
	// quotes.
	tick := w.tickCache.GetTickPrice(w.order.UserID, w.order.Symbol)
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
	sl := w.order.StopLoss

	// Calculate a safe margin (10% of SL distance) to prevent executing
	// too close to the Stop Loss. If price touches this bound, we reject
	// to avoid broker EA "Stop levels too close" errors.
	safeMargin := entry - sl
	if safeMargin < 0 {
		safeMargin = -safeMargin
	}
	safeMargin = safeMargin * 0.1

	switch w.order.Direction {
	case constants.DirectionLong:
		// For LONG: we buy at the Ask.
		// Price must be within [entry - tolerance, entry + tolerance]
		if tick.Ask < entry-tolerance || tick.Ask > entry+tolerance {
			return false
		}
		// Price must NOT be too close to or below the Stop Loss
		if sl > 0 && tick.Ask <= sl+safeMargin {
			return false
		}
		return true

	case constants.DirectionShort:
		// For SHORT: we sell at the Bid.
		// Price must be within [entry - tolerance, entry + tolerance]
		if tick.Bid < entry-tolerance || tick.Bid > entry+tolerance {
			return false
		}
		// Price must NOT be too close to or above the Stop Loss
		if sl > 0 && tick.Bid >= sl-safeMargin {
			return false
		}
		return true

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
			StopLoss:     w.order.StopLoss,
			HTFTimeframe: w.order.HTFTimeframe,
		}
	}

	result, err := w.gateway.ConfirmSetupWithParams(
		ctx, w.order.Symbol, w.order.AnalysisID, w.order.AnalysisID, params,
	)
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
	modeLabel := string(w.order.ExecutionMode)

	w.log.Warn().
		Str("execution_mode", modeLabel).
		Int("timeout_minutes", w.timeoutMinutes).
		Str("trading_style", string(w.order.TradingStyle)).
		Str("broker_order_id", w.order.BrokerOrderID).
		Msg("watcher_timed_out")

	observability.OrderPlacementTotal.WithLabelValues(modeLabel, "timeout").Inc()

	// For LIMIT orders, cancel the pending order at the broker.
	// The order has exceeded its TTL without being filled.
	if w.order.ExecutionMode == constants.ModeLimit && w.order.BrokerOrderID != "" {
		w.order.RLock()
		cancelCtx := w.order.IdentityCtx(context.Background())
		w.order.RUnlock()

		if err := w.broker.CancelOrder(cancelCtx, w.order.BrokerOrderID); err != nil {
			w.log.Error().Err(err).
				Str("broker_order_id", w.order.BrokerOrderID).
				Msg("limit_order_ttl_cancel_failed")
		} else {
			w.log.Info().
				Str("broker_order_id", w.order.BrokerOrderID).
				Int("timeout_minutes", w.timeoutMinutes).
				Str("trading_style", string(w.order.TradingStyle)).
				Msg("limit_order_ttl_expired_cancelled")
		}
	}

	if w.transport != nil {
		var message string
		if w.order.ExecutionMode == constants.ModeLimit {
			message = fmt.Sprintf("Limit order TTL expired for %s after %d minutes (%s style) — cancelled",
				w.order.Symbol, w.timeoutMinutes, w.order.TradingStyle)
		} else {
			message = fmt.Sprintf("Instant watcher timed out for %s after %d minutes (%s style)",
				w.order.Symbol, w.timeoutMinutes, w.order.TradingStyle)
		}

		w.transport.Publish(context.Background(),
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderExpired, alert.SeverityWarning,
				message).
				WithUserID(w.order.UserID).
				WithSymbol(w.order.Symbol).
				WithDirection(string(w.order.Direction)).
				WithDetails(map[string]interface{}{
					"watcher_id":       w.order.WatcherID,
					"analysis_id":      w.order.AnalysisID,
					"entry_price":      w.order.EntryPrice,
					"timeout_minutes":  w.timeoutMinutes,
					"trading_style":    string(w.order.TradingStyle),
					"execution_mode":   modeLabel,
					"broker_order_id":  w.order.BrokerOrderID,
				}),
		)
	}
}
