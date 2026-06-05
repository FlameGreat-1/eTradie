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

	// CheckNewsWindow asks the Gateway whether a high-impact economic
	// event affecting the symbol's currencies is imminent. The Gateway
	// owns the calendar; the watcher uses this on every LIMIT TTL tick
	// so a resting limit order can be cancelled before it fills into
	// news. tradingStyle selects the style-aware lockout window.
	CheckNewsWindow(ctx context.Context, symbol, tradingStyle, traceID string) (*NewsWindowResult, error)
}

// ConfirmResult holds the Gateway's response to a confirmation pulse.
type ConfirmResult struct {
	Confirmed       bool
	LTFConfirmation bool
	Reason          string
}

// NewsWindowResult holds the Gateway's news-proximity verdict for the
// LIMIT TTL loop. DataAvailable is false when the Gateway had no
// calendar data (it fails closed: Locked is then true).
type NewsWindowResult struct {
	Locked        bool
	DataAvailable bool
	Reason        string
	EventName     string
	Currency      string
	MinutesUntil  float64
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

// IdempotencyClearer is the contract to clear a failed idempotency record,
// allowing a previously failed cycle to be retried on subsequent analysis.
type IdempotencyClearer interface {
	Delete(ctx context.Context, userID, key string) error
}

// Manager tracks all active instant-mode watchers. Thread-safe.
// Provides Arm/Disarm lifecycle and coordinates graceful shutdown.
type Manager struct {
	broker      broker.Port
	gateway     GatewayPort
	audit       *audit.Logger
	transport   *alertredis.Transport
	store       WatcherPersistence
	usage       WatcherUsage
	idempotency IdempotencyClearer
	tickCache   *TickCache
	cfg         Config
	log         zerolog.Logger

	halt *cachedHaltReader

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

// WithIdempotency attaches an idempotency clearer. If a market order
// fails outright, the manager will use this to delete the idempotency
// record, unblocking subsequent attempts.
func (m *Manager) WithIdempotency(idc IdempotencyClearer) *Manager {
	m.mu.Lock()
	m.idempotency = idc
	m.mu.Unlock()
	return m
}

// WithHaltReader attaches the kill-switch reader consulted at the
// broker-firing moment. Optional; nil keeps the fire gate disabled.
func (m *Manager) WithHaltReader(hr HaltReader) *Manager {
	m.mu.Lock()
	if hr != nil {
		m.halt = newCachedHaltReader(hr)
	}
	m.mu.Unlock()
	return m
}

func (m *Manager) haltReader() *cachedHaltReader {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.halt
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
		order:       order,
		broker:      m.broker,
		gateway:     m.gateway,
		audit:       m.audit,
		transport:   m.transport,
		tickCache:   m.tickCache,
		cfg:         m.cfg,
		idempotency: m.idempotency,
		halt:        m.haltReader(),
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

// ActiveUserIDs returns the distinct, non-empty user IDs that own at
// least one currently-armed watcher. Used by the background
// token-refresh loop so it only mints fresh service tokens for owners
// that actually have a live watcher (instead of scanning the whole
// user table). Thread-safe; the per-Order field is read under the
// Order's own RLock so it never observes a partial identity update
// from RefreshUserOrderIdentity.
func (m *Manager) ActiveUserIDs() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	seen := make(map[string]struct{}, len(m.watchers))
	ids := make([]string, 0, len(m.watchers))
	for _, w := range m.watchers {
		w.order.RLock()
		uid := w.order.UserID
		w.order.RUnlock()
		if uid == "" {
			continue
		}
		if _, ok := seen[uid]; ok {
			continue
		}
		seen[uid] = struct{}{}
		ids = append(ids, uid)
	}
	return ids
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
	idempotency    IdempotencyClearer
	halt           *cachedHaltReader
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

// runLimitTTL is the run loop for LIMIT orders. It enforces the TTL
// timeout, cancels ahead of news, AND detects when the resting order
// fills at the broker so the filled position is handed off to Module C
// with its FULL trade intent (TP1/2/3 pct, rr, risk, style) instead of
// being lossily imported by the management reconciler (audit EM-C1).
//
// Two cadences run concurrently:
//   - fillTicker (fast, PollIntervalMs; min 1s): detect the fill quickly
//     so Module C starts TP2/TP3/break-even/trailing management with
//     minimal latency. The broker already holds SL+TP1 in the meantime.
//   - newsTicker (1 minute): news lockout + liveness, unchanged cadence.
func (w *Watcher) runLimitTTL(ctx context.Context) {
	fillInterval := time.Duration(w.cfg.PollIntervalMs) * time.Millisecond
	if fillInterval < time.Second {
		fillInterval = time.Second
	}
	fillTicker := time.NewTicker(fillInterval)
	defer fillTicker.Stop()

	newsTicker := time.NewTicker(1 * time.Minute)
	defer newsTicker.Stop()

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
		case <-fillTicker.C:
			// Detect a broker-side fill and hand the filled position off
			// to Module C. Returns true when the order has filled (or a
			// fatal handoff condition occurred) and the watcher must stop.
			if w.checkLimitFillAndHandoff(ctx) {
				return
			}
		case <-newsTicker.C:
			// Periodic liveness log so operators know the watcher is alive.
			w.log.Debug().
				Str("broker_order_id", w.order.BrokerOrderID).
				Msg("limit_watcher_ttl_check_alive")

			// News lockout (LIMIT lifetime, N1): a resting limit order
			// can fill autonomously at the broker, so it must not
			// outlive the approach of a high-impact event. The gateway
			// owns the calendar; ask it each tick (style-aware window).
			// An event beyond the calendar horizon at placement time
			// enters the lockout window as time advances and the macro
			// cache refreshes, so this tick loop closes that gap.
			if w.checkNewsAndCancel(ctx) {
				return
			}
		}
	}
}

// checkLimitFillAndHandoff polls the broker's open positions and, when
// the resting LIMIT order has filled, hands the filled position off to
// the Gateway (and thus Module C) carrying the order's FULL trade
// intent. Returns true when the watcher should stop (filled and handed
// off). A transient broker error is logged and ignored (false) so a
// blip never tears down a still-resting order.
//
// Fill correlation is by AnalysisID (the order was placed with
// Comment = AnalysisID, which MT5 carries onto the resulting position),
// falling back to symbol + direction when the broker does not echo the
// comment. The matched position's broker ticket becomes the trade's
// BrokerOrderID downstream; Module C's RegisterFilledTrade is idempotent
// on (user_id, broker_order_id) so a racing reconciler import is a no-op.
func (w *Watcher) checkLimitFillAndHandoff(ctx context.Context) bool {
	w.order.RLock()
	authCtx := w.order.IdentityCtx(ctx)
	symbol := w.order.Symbol
	direction := string(w.order.Direction)
	analysisID := w.order.AnalysisID
	entryPrice := w.order.EntryPrice
	w.order.RUnlock()

	positions, err := w.broker.GetPositions(authCtx)
	if err != nil {
		w.log.Warn().Err(err).Str("symbol", symbol).Msg("limit_watcher_fill_check_failed")
		return false
	}

	match := matchFilledPosition(positions, symbol, direction, analysisID, entryPrice)
	if match == nil {
		return false // Still resting (or not yet visible); keep watching.
	}

	// Slippage relative to the intended limit entry price.
	var slippage float64
	if entryPrice > 0 {
		slippage = match.EntryPrice - entryPrice
	}

	// Stamp the real position ticket so the handoff + any later disarm
	// reference the position, not the (now-consumed) pending order.
	w.order.Lock()
	w.order.BrokerOrderID = match.OrderID
	w.order.Unlock()

	w.log.Info().
		Str("symbol", symbol).
		Str("broker_order_id", match.OrderID).
		Str("analysis_id", analysisID).
		Float64("fill_price", match.EntryPrice).
		Float64("slippage", slippage).
		Float64("lot_size", match.LotSize).
		Msg("limit_order_fill_detected_handing_off")

	observability.OrderPlacementTotal.WithLabelValues(string(constants.ModeLimit), "filled").Inc()

	// Hand off to the Gateway with the FULL order context (carries
	// TP1/2/3 price+pct, rr, risk, style, setup) - identical contract to
	// the INSTANT path. The broker already holds SL+TP1 from placeLimit.
	if w.gateway != nil {
		if herr := w.gateway.NotifyExecutionCompleted(authCtx, w.order, match.OrderID, match.EntryPrice, slippage); herr != nil {
			w.log.Error().Err(herr).
				Str("symbol", symbol).
				Str("broker_order_id", match.OrderID).
				Msg("limit_fill_handoff_failed")
			// The position exists and is protected by broker SL+TP1; the
			// management reconciler will import it as the fallback. Stop
			// the watcher regardless - re-notifying on the next tick would
			// duplicate the handoff attempt for an already-open position.
			if w.transport != nil {
				w.transport.Publish(authCtx,
					alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityWarning,
						fmt.Sprintf("Limit order filled for %s but Module C handoff failed; reconciler will adopt it", symbol)).
						WithUserID(w.order.UserID).
						WithSymbol(symbol).
						WithDetail("broker_order_id", match.OrderID).
						WithDetail("analysis_id", analysisID),
				)
			}
			return true
		}
	}

	// Audit the fill (same as the instant path).
	w.audit.LogOrderPlaced(authCtx, w.order)

	if w.transport != nil {
		w.transport.Publish(authCtx,
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderPlaced, alert.SeverityInfo,
				fmt.Sprintf("Limit order FILLED for %s at %.5f", symbol, match.EntryPrice)).
				WithUserID(w.order.UserID).
				WithSymbol(symbol).
				WithDirection(direction).
				WithDetails(map[string]interface{}{
					"order_id":        w.order.OrderID,
					"broker_order_id": match.OrderID,
					"fill_price":      match.EntryPrice,
					"slippage":        slippage,
					"lot_size":        match.LotSize,
					"watcher_id":      w.order.WatcherID,
					"analysis_id":     analysisID,
				}),
		)
	}

	return true
}

// matchFilledPosition finds the open position corresponding to a filled
// LIMIT order, using three tiers of decreasing certainty:
//
//  1. Exact AnalysisID match (the order comment echoed onto the position).
//     Authoritative when the backend persists the comment (the native EA
//     always does; some MetaApi/broker combos may not).
//  2. Price-anchored: among symbol+direction matches, the position whose
//     open price is closest to the LIMIT order's set entry price (a LIMIT
//     fills at its price). Accepted only when that closest match is
//     unambiguous within a tight tolerance, so two same-symbol+direction
//     trades at different prices are still resolved correctly.
//  3. symbol+direction with exactly one open position (legacy fallback).
//
// Returns nil when no tier yields a confident match (still resting or not
// yet visible) so the watcher keeps polling.
func matchFilledPosition(positions []models.Position, symbol, direction, analysisID string, orderEntryPrice float64) *models.Position {
	// Tier 1: exact AnalysisID match.
	if analysisID != "" {
		for i := range positions {
			if positions[i].AnalysisID == analysisID {
				return &positions[i]
			}
		}
	}

	// Collect symbol+direction candidates once for tiers 2 and 3.
	var candidates []*models.Position
	for i := range positions {
		if positions[i].Symbol == symbol && positions[i].Direction == direction {
			candidates = append(candidates, &positions[i])
		}
	}

	if len(candidates) == 1 {
		return candidates[0] // Tier 3 (also the common case).
	}
	if len(candidates) == 0 {
		return nil
	}

	// Tier 2: price-anchored. A LIMIT order fills at its set entry price,
	// so the matching position's open price is closest to it. Require the
	// best candidate to be clearly closest (the runner-up must be at least
	// 2x further away) so we never mis-attribute on near-equal prices.
	if orderEntryPrice > 0 {
		bestIdx, bestDist, secondDist := -1, 0.0, 0.0
		for i, c := range candidates {
			d := c.EntryPrice - orderEntryPrice
			if d < 0 {
				d = -d
			}
			if bestIdx == -1 || d < bestDist {
				secondDist = bestDist
				bestDist = d
				bestIdx = i
			} else if secondDist == 0.0 || d < secondDist {
				secondDist = d
			}
		}
		// Unambiguous when the runner-up is clearly further (>=2x) than the
		// best, OR there is effectively only one near-price candidate.
		if bestIdx != -1 && (secondDist == 0.0 || secondDist >= 2*bestDist) {
			return candidates[bestIdx]
		}
	}

	// Ambiguous: cannot attribute the fill confidently; keep waiting.
	return nil
}

// checkNewsAndCancel asks the Gateway whether news is imminent for this
// order's symbol and, if so, cancels the resting limit order at the
// broker and reports true (watcher should stop). A transient gateway
// error is logged and ignored (false) so a gateway blip never cancels
// a valid order; the gateway fails closed on missing calendar data,
// which arrives here as Locked=true and does trigger the cancel.
func (w *Watcher) checkNewsAndCancel(ctx context.Context) bool {
	if w.gateway == nil {
		return false
	}

	w.order.RLock()
	authCtx := w.order.IdentityCtx(ctx)
	symbol := w.order.Symbol
	style := string(w.order.TradingStyle)
	analysisID := w.order.AnalysisID
	brokerOrderID := w.order.BrokerOrderID
	w.order.RUnlock()

	news, err := w.gateway.CheckNewsWindow(authCtx, symbol, style, analysisID)
	if err != nil {
		w.log.Warn().Err(err).Str("symbol", symbol).Msg("limit_watcher_news_check_failed")
		return false
	}
	if !news.Locked {
		return false
	}

	w.log.Warn().
		Str("symbol", symbol).
		Str("reason", news.Reason).
		Str("event_name", news.EventName).
		Str("currency", news.Currency).
		Float64("minutes_until", news.MinutesUntil).
		Bool("data_available", news.DataAvailable).
		Str("broker_order_id", brokerOrderID).
		Msg("limit_order_cancelled_for_news_lockout")

	if brokerOrderID != "" {
		if cancelErr := w.broker.CancelOrder(authCtx, brokerOrderID); cancelErr != nil {
			w.log.Error().Err(cancelErr).
				Str("broker_order_id", brokerOrderID).
				Msg("limit_order_news_cancel_failed")
			// The order may still fill into news; surface critically.
			if w.transport != nil {
				w.transport.Publish(authCtx,
					alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityCritical,
						fmt.Sprintf("CRITICAL: failed to cancel %s limit order ahead of news: %s", symbol, cancelErr.Error())).
						WithUserID(w.order.UserID).
						WithSymbol(symbol).
						WithDetail("broker_order_id", brokerOrderID).
						WithDetail("reason", string(constants.ReasonNewsLockout)),
				)
			}
			// Stop the watcher regardless: continuing to poll cannot
			// un-fill an order, and a duplicate cancel next tick adds no
			// value. Operators are alerted for manual reconciliation.
			return true
		}
	}

	observability.OrderPlacementTotal.WithLabelValues(string(constants.ModeLimit), "news_cancelled").Inc()

	if w.transport != nil {
		w.transport.Publish(authCtx,
			alert.NewEvent(alert.SourceExecution, alert.TypeOrderCancelled, alert.SeverityWarning,
				fmt.Sprintf("Limit order for %s cancelled ahead of high-impact news: %s", symbol, news.Reason)).
				WithUserID(w.order.UserID).
				WithSymbol(symbol).
				WithDirection(string(w.order.Direction)).
				WithDetails(map[string]interface{}{
					"watcher_id":      w.order.WatcherID,
					"analysis_id":     analysisID,
					"broker_order_id": brokerOrderID,
					"reason":          string(constants.ReasonNewsLockout),
					"event_name":      news.EventName,
					"currency":        news.Currency,
					"minutes_until":   news.MinutesUntil,
				}),
		)
	}

	return true
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
	// Kill-switch fire gate: an engaged global/per-user halt blocks
	// placement of this already-armed watcher. Analysis is unaffected;
	// only the irreversible broker call is stopped. Disarm so the
	// watcher does not spin retrying a blocked fire.
	if halted, scope := w.halt.halted(ctx, w.order.UserID); halted {
		w.log.Warn().Str("scope", scope).Msg("watcher_fire_blocked_by_kill_switch")
		w.audit.LogExecutionHalted(ctx, w.order.ToTradeRequest(),
			"execution kill switch engaged ("+scope+" scope): instant order placement blocked")
		if w.transport != nil {
			w.transport.Publish(ctx,
				alert.NewEvent(alert.SourceExecution, alert.TypeExecutionHalted, alert.SeverityCritical,
					fmt.Sprintf("Instant order blocked for %s: execution halted (%s)", w.order.Symbol, scope)).
					WithUserID(w.order.UserID).
					WithSymbol(w.order.Symbol).
					WithDirection(string(w.order.Direction)).
					WithDetails(map[string]interface{}{
						"watcher_id":  w.order.WatcherID,
						"analysis_id": w.order.AnalysisID,
						"scope":       scope,
					}),
			)
		}
		return true
	}

	placement := &models.OrderPlacement{
		Symbol:    w.order.Symbol,
		Direction: constants.BrokerDirection(w.order.Direction),
		OrderType: string(constants.BrokerOrderMarket),
		Price:     0, // Market order — broker fills at best available.
		StopLoss:  w.order.StopLoss,
		// Attach the FINAL target (TP3) to the broker, not TP1: a
		// position-level TP closes the whole position, so the broker TP
		// must sit beyond the software TP1/TP2 partials (CRITICAL).
		TakeProfit: w.order.BrokerTakeProfit(),
		LotSize:    w.order.LotSize,
		Comment:    w.order.AnalysisID,
	}

	result, err := w.broker.PlaceMarketOrder(ctx, placement)
	if err != nil {
		w.log.Error().Err(err).Msg("watcher_market_order_failed")

		if w.idempotency != nil {
			idemKey := w.order.IdempotencyKey
			if idemKey == "" {
				idemKey = w.order.OrderID
			}
			if clErr := w.idempotency.Delete(ctx, w.order.UserID, idemKey); clErr != nil {
				w.log.Warn().Err(clErr).Msg("failed_to_clear_idempotency_after_market_order_failure")
			}
		}

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
	//
	// EM-M2: re-derive the realized risk from the ACTUAL fill price. The
	// order was sized + min-stop-validated against the entry-zone midpoint
	// (w.order.EntryPrice), but a market fill lands anywhere in the zone
	// +/- overshoot tolerance, so the realized SL distance (fill -> SL)
	// differs from the sized distance (midpoint -> SL). Risk scales
	// linearly with SL distance at a fixed lot size, so rescaling
	// RiskAmount by the distance ratio is exact and needs no pip metadata.
	// Read the sized distance BEFORE mutating anything; skip on degenerate
	// inputs so a bad tick never zeroes the risk.
	w.order.Lock()
	w.order.BrokerOrderID = result.BrokerOrderID
	if result.FillPrice > 0 && w.order.StopLoss > 0 {
		sizedDist := w.order.EntryPrice - w.order.StopLoss
		if sizedDist < 0 {
			sizedDist = -sizedDist
		}
		realizedDist := result.FillPrice - w.order.StopLoss
		if realizedDist < 0 {
			realizedDist = -realizedDist
		}
		if sizedDist > 0 && realizedDist > 0 && w.order.RiskAmount > 0 {
			w.order.RiskAmount = w.order.RiskAmount * (realizedDist / sizedDist)
		}
	}
	realizedRisk := w.order.RiskAmount
	w.order.Unlock()

	w.log.Info().
		Str("broker_order_id", result.BrokerOrderID).
		Float64("fill_price", result.FillPrice).
		Float64("slippage", result.Slippage).
		Float64("lot_size", w.order.LotSize).
		Float64("realized_risk_amount", realizedRisk).
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
