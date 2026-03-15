package state

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/store"
)

// Manager maintains execution state with in-memory caching backed by
// PostgreSQL for P&L persistence. Positions and pending orders are
// refreshed from the broker on every execution attempt. P&L counters
// are persisted to survive service restarts. Thread-safe via mutex.
type Manager struct {
	mu sync.RWMutex

	positions     []models.Position
	pendingOrders []models.BrokerPendingOrder
	account       *models.AccountInfo

	dailyPnL        float64
	weeklyPnL       float64
	dailyPeriodKey  string
	weeklyPeriodKey string

	broker   broker.Port
	pnlStore *store.PnLStore
	log      zerolog.Logger
}

// NewManager creates a state manager backed by the given broker port
// and P&L store. Loads current P&L from PostgreSQL on construction
// so counters survive service restarts.
func NewManager(bp broker.Port, pnlStore *store.PnLStore) *Manager {
	now := time.Now().UTC()
	m := &Manager{
		broker:          bp,
		pnlStore:        pnlStore,
		dailyPeriodKey:  store.DailyPeriodKey(now),
		weeklyPeriodKey: store.WeeklyPeriodKey(now),
		log:             observability.Logger("state_manager"),
	}

	// Load persisted P&L from PostgreSQL.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	snap, err := pnlStore.LoadCurrent(ctx)
	if err != nil {
		m.log.Error().Err(err).Msg("pnl_load_on_startup_failed")
	} else {
		m.dailyPnL = snap.DailyPnL
		m.weeklyPnL = snap.WeeklyPnL
		m.dailyPeriodKey = snap.DailyPeriodKey
		m.weeklyPeriodKey = snap.WeeklyPeriodKey
		m.log.Info().
			Float64("daily_pnl", snap.DailyPnL).
			Int("daily_trades", snap.DailyTrades).
			Float64("weekly_pnl", snap.WeeklyPnL).
			Int("weekly_trades", snap.WeeklyTrades).
			Msg("pnl_restored_from_db")
	}

	return m
}

// Refresh fetches live state from the broker. Called before every
// execution attempt to ensure accuracy. Detects day/week boundary
// crossings and reloads P&L from PostgreSQL with new period keys.
func (m *Manager) Refresh(ctx context.Context) error {
	account, err := m.broker.GetAccountInfo(ctx)
	if err != nil {
		return err
	}

	positions, err := m.broker.GetPositions(ctx)
	if err != nil {
		return err
	}

	pending, err := m.broker.GetPendingOrders(ctx)
	if err != nil {
		return err
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	m.account = account
	m.positions = positions
	m.pendingOrders = pending

	// Detect day/week boundary crossings and reload from DB.
	now := time.Now().UTC()
	newDailyKey := store.DailyPeriodKey(now)
	newWeeklyKey := store.WeeklyPeriodKey(now)

	boundaryChanged := false
	if newDailyKey != m.dailyPeriodKey {
		m.dailyPeriodKey = newDailyKey
		m.dailyPnL = 0
		boundaryChanged = true
	}
	if newWeeklyKey != m.weeklyPeriodKey {
		m.weeklyPeriodKey = newWeeklyKey
		m.weeklyPnL = 0
		boundaryChanged = true
	}

	if boundaryChanged {
		// Reload from DB to pick up any P&L recorded by other instances
		// or from trades closed during the new period.
		snap, err := m.pnlStore.LoadCurrent(ctx)
		if err != nil {
			m.log.Error().Err(err).Msg("pnl_reload_on_boundary_failed")
		} else {
			m.dailyPnL = snap.DailyPnL
			m.weeklyPnL = snap.WeeklyPnL
		}
	}

	observability.OpenPositionCount.Set(float64(len(m.positions)))
	observability.PendingOrderCount.Set(float64(len(m.pendingOrders)))
	observability.DailyPnL.Set(m.dailyPnL)
	observability.WeeklyPnL.Set(m.weeklyPnL)

	m.log.Debug().
		Int("positions", len(m.positions)).
		Int("pending", len(m.pendingOrders)).
		Float64("balance", account.Balance).
		Float64("daily_pnl", m.dailyPnL).
		Float64("weekly_pnl", m.weeklyPnL).
		Str("daily_key", m.dailyPeriodKey).
		Str("weekly_key", m.weeklyPeriodKey).
		Msg("state_refreshed")

	return nil
}

// OpenPositionCount returns the number of open positions.
func (m *Manager) OpenPositionCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.positions)
}

// HasPositionOnPair returns true if there is an open position or
// pending order on the given symbol.
func (m *Manager) HasPositionOnPair(symbol string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	norm := strings.ToUpper(symbol)
	for i := range m.positions {
		if strings.ToUpper(m.positions[i].Symbol) == norm {
			return true
		}
	}
	for i := range m.pendingOrders {
		if strings.ToUpper(m.pendingOrders[i].Symbol) == norm {
			return true
		}
	}
	return false
}

// HasCorrelatedExposure returns true if there is an open position or
// pending order on any pair in the same correlation group as symbol.
func (m *Manager) HasCorrelatedExposure(symbol string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	norm := strings.ToUpper(symbol)
	for i := range m.positions {
		posSymbol := strings.ToUpper(m.positions[i].Symbol)
		if posSymbol != norm && AreCorrelated(norm, posSymbol) {
			return true
		}
	}
	for i := range m.pendingOrders {
		ordSymbol := strings.ToUpper(m.pendingOrders[i].Symbol)
		if ordSymbol != norm && AreCorrelated(norm, ordSymbol) {
			return true
		}
	}
	return false
}

// DailyLossPercent returns the daily realized loss as a percentage
// of account balance. Returns 0 if no loss.
func (m *Manager) DailyLossPercent() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.account == nil || m.account.Balance <= 0 {
		return 0
	}
	if m.dailyPnL >= 0 {
		return 0
	}
	return (-m.dailyPnL / m.account.Balance) * 100
}

// WeeklyDrawdownPercent returns the weekly realized loss as a
// percentage of account balance. Returns 0 if no loss.
func (m *Manager) WeeklyDrawdownPercent() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.account == nil || m.account.Balance <= 0 {
		return 0
	}
	if m.weeklyPnL >= 0 {
		return 0
	}
	return (-m.weeklyPnL / m.account.Balance) * 100
}

// RecordPnL persists a realized P&L amount to PostgreSQL and updates
// in-memory counters. Called by Module C when a trade closes.
// DB write is the source of truth; in-memory is updated only on success.
func (m *Manager) RecordPnL(ctx context.Context, amount float64) error {
	if err := m.pnlStore.RecordPnL(ctx, amount); err != nil {
		m.log.Error().Err(err).Float64("amount", amount).Msg("pnl_persist_failed")
		return err
	}

	m.mu.Lock()
	m.dailyPnL += amount
	m.weeklyPnL += amount
	observability.DailyPnL.Set(m.dailyPnL)
	observability.WeeklyPnL.Set(m.weeklyPnL)
	m.mu.Unlock()

	return nil
}

// Positions returns a copy of current open positions.
func (m *Manager) Positions() []models.Position {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]models.Position, len(m.positions))
	copy(out, m.positions)
	return out
}

// PendingOrders returns a copy of current pending orders.
func (m *Manager) PendingOrders() []models.BrokerPendingOrder {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]models.BrokerPendingOrder, len(m.pendingOrders))
	copy(out, m.pendingOrders)
	return out
}

// Account returns a copy of the current account info.
func (m *Manager) Account() *models.AccountInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.account == nil {
		return nil
	}
	cpy := *m.account
	return &cpy
}

// DailyPnL returns the current daily realized P&L.
func (m *Manager) DailyPnL() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.dailyPnL
}

// WeeklyPnL returns the current weekly realized P&L.
func (m *Manager) WeeklyPnL() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.weeklyPnL
}
