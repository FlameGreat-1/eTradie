package state

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
)

// userState holds execution state for a single user. Each user has
// their own positions, pending orders, account info, and P&L counters
// because each user has their own MT5 broker account.
type userState struct {
	positions     []models.Position
	pendingOrders []models.BrokerPendingOrder
	account       *models.AccountInfo

	dailyPnL        float64
	weeklyPnL       float64
	dailyPeriodKey  string
	weeklyPeriodKey string
}

// Manager maintains per-user execution state with in-memory caching
// backed by PostgreSQL for P&L persistence. Positions and pending
// orders are refreshed from the broker on every execution attempt.
// P&L counters are persisted to survive service restarts. Thread-safe
// via mutex protecting the user state map.
type Manager struct {
	mu sync.RWMutex

	users map[string]*userState // keyed by userID

	broker   broker.Port
	pnlStore *store.PnLStore
	log      zerolog.Logger
}

// NewManager creates a state manager backed by the given broker port
// and P&L store. Per-user state is lazily initialized on first access.
func NewManager(bp broker.Port, pnlStore *store.PnLStore) *Manager {
	m := &Manager{
		users:    make(map[string]*userState),
		broker:   bp,
		pnlStore: pnlStore,
		log:      observability.Logger("state_manager"),
	}

	m.log.Info().Msg("state_manager_created_per_user_state")
	return m
}

// getOrCreateUser returns the userState for the given userID, creating
// it if it doesn't exist. Must be called with mu held (write lock).
func (m *Manager) getOrCreateUser(userID string) *userState {
	us, exists := m.users[userID]
	if !exists {
		now := time.Now().UTC()
		us = &userState{
			dailyPeriodKey:  store.DailyPeriodKey(now),
			weeklyPeriodKey: store.WeeklyPeriodKey(now),
		}
		m.users[userID] = us
	}
	return us
}

// getUserRead returns the userState for reading, or nil if not found.
// Must be called with mu held (read lock).
func (m *Manager) getUserRead(userID string) *userState {
	return m.users[userID]
}

// Refresh fetches live state from the broker for the given user.
// Called before every execution attempt to ensure accuracy. Detects
// day/week boundary crossings and reloads P&L from PostgreSQL with
// new period keys.
//
// Each broker call is independent: a ZMQ timeout on one endpoint
// does NOT cancel the others. This is critical because the engine
// serializes ZMQ calls behind a single lock — three concurrent
// requests frequently cause the 2nd or 3rd to timeout while the
// 1st holds the lock, and the old errgroup behaviour propagated
// that single timeout into a full 503 for the dashboard. Now each
// call either succeeds or logs a warning and falls back to the
// previously cached state (nil / empty slice).
func (m *Manager) Refresh(ctx context.Context, userID string) error {
	var account *models.AccountInfo
	var positions []models.Position
	var pending []models.BrokerPendingOrder

	// --- independent calls (no errgroup) ---
	var accErr, posErr, pendErr error

	type accResult struct {
		info *models.AccountInfo
		err  error
	}
	type posResult struct {
		pos []models.Position
		err error
	}
	type pendResult struct {
		ord []models.BrokerPendingOrder
		err error
	}

	accCh := make(chan accResult, 1)
	posCh := make(chan posResult, 1)
	pendCh := make(chan pendResult, 1)

	go func() {
		info, err := m.broker.GetAccountInfo(ctx)
		accCh <- accResult{info, err}
	}()
	go func() {
		pos, err := m.broker.GetPositions(ctx)
		posCh <- posResult{pos, err}
	}()
	go func() {
		ord, err := m.broker.GetPendingOrders(ctx)
		pendCh <- pendResult{ord, err}
	}()

	ar := <-accCh
	account, accErr = ar.info, ar.err

	pr := <-posCh
	positions, posErr = pr.pos, pr.err

	pdr := <-pendCh
	pending, pendErr = pdr.ord, pdr.err

	// Log individual failures but do NOT return an error unless the
	// account call (essential for P&L guards) failed.
	if posErr != nil {
		m.log.Warn().Err(posErr).Str("user_id", userID).Msg("refresh_positions_failed_using_stale")
	}
	if pendErr != nil {
		m.log.Warn().Err(pendErr).Str("user_id", userID).Msg("refresh_pending_orders_failed_using_stale")
	}
	if accErr != nil {
		m.log.Warn().Err(accErr).Str("user_id", userID).Msg("refresh_account_info_failed")
		// Account is required for risk guards; propagate this error.
		return accErr
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	us := m.getOrCreateUser(userID)

	us.account = account
	us.positions = positions
	us.pendingOrders = pending

	// Detect day/week boundary crossings and reload from DB.
	now := time.Now().UTC()
	newDailyKey := store.DailyPeriodKey(now)
	newWeeklyKey := store.WeeklyPeriodKey(now)

	boundaryChanged := false
	if newDailyKey != us.dailyPeriodKey {
		us.dailyPeriodKey = newDailyKey
		us.dailyPnL = 0
		boundaryChanged = true
	}
	if newWeeklyKey != us.weeklyPeriodKey {
		us.weeklyPeriodKey = newWeeklyKey
		us.weeklyPnL = 0
		boundaryChanged = true
	}

	if boundaryChanged {
		snap, err := m.pnlStore.LoadCurrent(ctx, userID)
		if err != nil {
			m.log.Error().Err(err).Str("user_id", userID).Msg("pnl_reload_on_boundary_failed")
		} else {
			us.dailyPnL = snap.DailyPnL
			us.weeklyPnL = snap.WeeklyPnL
		}
	}

	observability.OpenPositionCount.Set(float64(len(us.positions)))
	observability.PendingOrderCount.Set(float64(len(us.pendingOrders)))
	observability.DailyPnL.Set(us.dailyPnL)
	observability.WeeklyPnL.Set(us.weeklyPnL)

	m.log.Debug().
		Str("user_id", userID).
		Int("positions", len(us.positions)).
		Int("pending", len(us.pendingOrders)).
		Float64("balance", account.Balance).
		Float64("daily_pnl", us.dailyPnL).
		Float64("weekly_pnl", us.weeklyPnL).
		Str("daily_key", us.dailyPeriodKey).
		Str("weekly_key", us.weeklyPeriodKey).
		Msg("state_refreshed")

	return nil
}

// OpenPositionCount returns the number of open positions for the user.
func (m *Manager) OpenPositionCount(userID string) int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return 0
	}
	return len(us.positions)
}

// HasPositionOnPair returns true if the user has an open position or
// pending order on the given symbol.
func (m *Manager) HasPositionOnPair(userID, symbol string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return false
	}
	norm := strings.ToUpper(symbol)
	for i := range us.positions {
		if strings.ToUpper(us.positions[i].Symbol) == norm {
			return true
		}
	}
	for i := range us.pendingOrders {
		if strings.ToUpper(us.pendingOrders[i].Symbol) == norm {
			return true
		}
	}
	return false
}

// HasCorrelatedExposure returns true if the user has an open position
// or pending order on any pair in the same correlation group as symbol.
func (m *Manager) HasCorrelatedExposure(userID, symbol string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return false
	}
	norm := strings.ToUpper(symbol)
	for i := range us.positions {
		posSymbol := strings.ToUpper(us.positions[i].Symbol)
		if posSymbol != norm && AreCorrelated(norm, posSymbol) {
			return true
		}
	}
	for i := range us.pendingOrders {
		ordSymbol := strings.ToUpper(us.pendingOrders[i].Symbol)
		if ordSymbol != norm && AreCorrelated(norm, ordSymbol) {
			return true
		}
	}
	return false
}

// DailyLossPercent returns the user's daily realized loss as a
// percentage of account balance. Returns 0 if no loss.
func (m *Manager) DailyLossPercent(userID string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil || us.account == nil || us.account.Balance <= 0 {
		return 0
	}
	if us.dailyPnL >= 0 {
		return 0
	}
	return (-us.dailyPnL / us.account.Balance) * 100
}

// WeeklyDrawdownPercent returns the user's weekly realized loss as a
// percentage of account balance. Returns 0 if no loss.
func (m *Manager) WeeklyDrawdownPercent(userID string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil || us.account == nil || us.account.Balance <= 0 {
		return 0
	}
	if us.weeklyPnL >= 0 {
		return 0
	}
	return (-us.weeklyPnL / us.account.Balance) * 100
}

// RecordPnL persists a realized P&L amount to PostgreSQL and updates
// in-memory counters for the user. Called by Module C when a trade
// closes. DB write is the source of truth; in-memory is updated only
// on success.
func (m *Manager) RecordPnL(ctx context.Context, userID string, amount float64) error {
	if err := m.pnlStore.RecordPnL(ctx, userID, amount); err != nil {
		m.log.Error().Err(err).Str("user_id", userID).Float64("amount", amount).Msg("pnl_persist_failed")
		return err
	}

	m.mu.Lock()
	us := m.getOrCreateUser(userID)
	us.dailyPnL += amount
	us.weeklyPnL += amount
	observability.DailyPnL.Set(us.dailyPnL)
	observability.WeeklyPnL.Set(us.weeklyPnL)
	m.mu.Unlock()

	return nil
}

// Positions returns a copy of the user's current open positions.
func (m *Manager) Positions(userID string) []models.Position {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return nil
	}
	out := make([]models.Position, len(us.positions))
	copy(out, us.positions)
	return out
}

// PendingOrders returns a copy of the user's current pending orders.
func (m *Manager) PendingOrders(userID string) []models.BrokerPendingOrder {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return nil
	}
	out := make([]models.BrokerPendingOrder, len(us.pendingOrders))
	copy(out, us.pendingOrders)
	return out
}

// Account returns a copy of the user's current account info.
func (m *Manager) Account(userID string) *models.AccountInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil || us.account == nil {
		return nil
	}
	cpy := *us.account
	return &cpy
}

// DailyPnL returns the user's current daily realized P&L.
func (m *Manager) DailyPnL(userID string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return 0
	}
	return us.dailyPnL
}

// WeeklyPnL returns the user's current weekly realized P&L.
func (m *Manager) WeeklyPnL(userID string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	us := m.getUserRead(userID)
	if us == nil {
		return 0
	}
	return us.weeklyPnL
}

// ActiveUserIDs returns the snapshot of user ids that have a tracked
// state entry. Used by the broker reconciler to iterate over users
// whose broker state should be sync-checked. Order is not
// guaranteed; callers must not rely on it.
func (m *Manager) ActiveUserIDs() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]string, 0, len(m.users))
	for uid := range m.users {
		out = append(out, uid)
	}
	return out
}

// AdoptBrokerPosition adds a broker-reported position to the user's
// in-memory slice if no entry with the same OrderID already exists.
// Called by the reconciler when the broker reports a position the
// engine did not previously know about (broker_only drift).
// Idempotent.
func (m *Manager) AdoptBrokerPosition(userID string, p *models.Position) {
	if userID == "" || p == nil || p.OrderID == "" {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	us := m.getOrCreateUser(userID)
	for i := range us.positions {
		if us.positions[i].OrderID == p.OrderID {
			return // already tracked
		}
	}
	us.positions = append(us.positions, *p)
	observability.OpenPositionCount.Set(float64(len(us.positions)))
}

// ReplaceBrokerPosition overwrites the engine's in-memory copy of a
// position with the broker-reported one (mismatch drift). The broker
// is the source of truth for SL/TP/lot-size; the engine adopts.
func (m *Manager) ReplaceBrokerPosition(userID string, p *models.Position) {
	if userID == "" || p == nil || p.OrderID == "" {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	us := m.getOrCreateUser(userID)
	for i := range us.positions {
		if us.positions[i].OrderID == p.OrderID {
			us.positions[i] = *p
			return
		}
	}
	// Not present yet - same as adopt.
	us.positions = append(us.positions, *p)
	observability.OpenPositionCount.Set(float64(len(us.positions)))
}

// RemoveGhostPosition deletes a position the broker no longer
// reports. Returns true when an entry was actually removed.
//
// Called by the reconciler's ghost-position branch when the engine's
// view contains a position that:
//
//	(a) is NOT in the current broker positions list, AND
//	(b) was present in the last persisted positions snapshot >= the
//	    configured ghost-position min-age threshold ago.
//
// Together, those two facts say 'the broker closed this cleanly
// between cycles'. The engine adopts the close.
//
// Idempotent: returns false when the user is unknown OR the
// broker_order_id is not in the slice. The OpenPositionCount gauge
// is updated atomically with the in-memory mutation.
//
// Audit ref: CHECKLIST Section 7 'No ghost positions'.
func (m *Manager) RemoveGhostPosition(userID, brokerOrderID string) bool {
	if userID == "" || brokerOrderID == "" {
		return false
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	us := m.getUserRead(userID)
	if us == nil {
		return false
	}
	for i := range us.positions {
		if us.positions[i].OrderID == brokerOrderID {
			us.positions = append(us.positions[:i], us.positions[i+1:]...)
			observability.OpenPositionCount.Set(float64(len(us.positions)))
			return true
		}
	}
	return false
}
