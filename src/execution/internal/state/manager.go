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
)

// Manager maintains in-memory execution state, refreshed from the
// broker on every execution attempt. Thread-safe via mutex.
type Manager struct {
	mu sync.RWMutex

	positions     []models.Position
	pendingOrders []models.BrokerPendingOrder
	account       *models.AccountInfo

	dailyPnL       float64
	weeklyPnL      float64
	dailyResetDay  int // Day of year for daily reset.
	dailyResetYear int // Year for daily reset (handles year boundary).
	weeklyResetDay int // Day of year for weekly reset (Monday).
	weeklyResetYr  int // Year for weekly reset.

	broker broker.Port
	log    zerolog.Logger
}

// NewManager creates a state manager backed by the given broker port.
func NewManager(bp broker.Port) *Manager {
	now := time.Now().UTC()
	return &Manager{
		broker:         bp,
		dailyResetDay:  now.YearDay(),
		dailyResetYear: now.Year(),
		weeklyResetDay: mondayYearDay(now),
		weeklyResetYr:  mondayYear(now),
		log:            observability.Logger("state_manager"),
	}
}

// Refresh fetches live state from the broker. Called before every
// execution attempt to ensure accuracy.
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

	// Reset daily/weekly P&L counters on day/week boundaries.
	now := time.Now().UTC()
	if now.YearDay() != m.dailyResetDay || now.Year() != m.dailyResetYear {
		m.dailyPnL = 0
		m.dailyResetDay = now.YearDay()
		m.dailyResetYear = now.Year()
	}
	currentMonday := mondayYearDay(now)
	currentMondayYr := mondayYear(now)
	if currentMonday != m.weeklyResetDay || currentMondayYr != m.weeklyResetYr {
		m.weeklyPnL = 0
		m.weeklyResetDay = currentMonday
		m.weeklyResetYr = currentMondayYr
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

// RecordPnL adds a realized P&L amount to daily and weekly counters.
// Called by Module C when a trade closes.
func (m *Manager) RecordPnL(amount float64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.dailyPnL += amount
	m.weeklyPnL += amount
	observability.DailyPnL.Set(m.dailyPnL)
	observability.WeeklyPnL.Set(m.weeklyPnL)
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

func mondayYearDay(t time.Time) int {
	offset := int(t.Weekday()) - int(time.Monday)
	if offset < 0 {
		offset += 7
	}
	monday := t.AddDate(0, 0, -offset)
	return monday.YearDay()
}

func mondayYear(t time.Time) int {
	offset := int(t.Weekday()) - int(time.Monday)
	if offset < 0 {
		offset += 7
	}
	monday := t.AddDate(0, 0, -offset)
	return monday.Year()
}
