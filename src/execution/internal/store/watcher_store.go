package store

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// WatcherStore handles persistence of pending instant-mode watchers
// so they survive service restarts. All operations are scoped by
// watcher_id (unique) and user_id for multi-tenant isolation.
type WatcherStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewWatcherStore creates a watcher persistence store.
func NewWatcherStore(pool *pgxpool.Pool) *WatcherStore {
	return &WatcherStore{
		pool: pool,
		log:  observability.Logger("watcher_store"),
	}
}

// PendingWatcherRecord is the database model for a persisted watcher.
type PendingWatcherRecord struct {
	WatcherID          string
	OrderID            string
	UserID             string
	Symbol             string
	Direction          string
	ExecutionMode      string
	EntryPrice         float64
	StopLoss           float64
	TP1Price           float64
	TP1Pct             int32
	TP2Price           float64
	TP2Pct             int32
	TP3Price           float64
	TP3Pct             int32
	LotSize            float64
	RiskPercent        float64
	RiskAmount         float64
	RRRatio            float64
	AccountBalance     float64
	SLDistancePips     float64
	PipValue           float64
	OvershootTolerance float64
	LTFConfirmed       bool
	AnalysisID         string
	TradingStyle       string
	Session            string
	Grade              string
	Confluence         float64
	Confidence         float64
	SetupType          string
	TraceID            string
	CreatedAt          time.Time
}

// Insert persists a pending watcher to the database.
// Called when a watcher is armed via Arm().
func (s *WatcherStore) Insert(ctx context.Context, order *models.Order) error {
	if order.UserID == "" {
		return fmt.Errorf("insert watcher %s: user_id must not be empty", order.WatcherID)
	}

	_, err := s.pool.Exec(ctx, `
		INSERT INTO execution_pending_watchers (
			watcher_id, order_id, user_id, symbol, direction, execution_mode,
			entry_price, stop_loss, tp1_price, tp1_pct, tp2_price, tp2_pct,
			tp3_price, tp3_pct, lot_size, risk_percent, risk_amount, rr_ratio,
			account_balance, sl_distance_pips, pip_value, overshoot_tolerance,
			ltf_confirmed, analysis_id, trading_style, session, grade,
			confluence, confidence, setup_type, status, created_at
		) VALUES (
			$1, $2, $3, $4, $5, $6,
			$7, $8, $9, $10, $11, $12,
			$13, $14, $15, $16, $17, $18,
			$19, $20, $21, $22,
			$23, $24, $25, $26, $27,
			$28, $29, $30, 'PENDING', $31
		)
		ON CONFLICT (watcher_id) DO NOTHING`,
		order.WatcherID, order.OrderID, order.UserID, order.Symbol,
		string(order.Direction), string(order.ExecutionMode),
		order.EntryPrice, order.StopLoss, order.TP1Price, order.TP1Pct,
		order.TP2Price, order.TP2Pct, order.TP3Price, order.TP3Pct,
		order.LotSize, order.RiskPercent, order.RiskAmount, order.RRRatio,
		order.AccountBalance, order.SLDistancePips, order.PipValue,
		order.OvershootTolerance, order.LTFConfirmed, order.AnalysisID,
		string(order.TradingStyle), order.Session, order.Grade,
		order.Confluence, order.Confidence, order.SetupType,
		order.CreatedAt,
	)
	if err != nil {
		return fmt.Errorf("insert watcher %s: %w", order.WatcherID, err)
	}

	s.log.Info().
		Str("watcher_id", order.WatcherID).
		Str("user_id", order.UserID).
		Str("symbol", order.Symbol).
		Msg("watcher_persisted")
	return nil
}

// Delete removes a watcher from the pending table.
// Called when a watcher completes (order filled), times out, or is disarmed.
func (s *WatcherStore) Delete(ctx context.Context, watcherID string) error {
	_, err := s.pool.Exec(ctx,
		`DELETE FROM execution_pending_watchers WHERE watcher_id = $1`,
		watcherID,
	)
	if err != nil {
		return fmt.Errorf("delete watcher %s: %w", watcherID, err)
	}
	return nil
}

// GetAllPending returns all watchers with status='PENDING'.
// Used on service restart to restore monitoring for pending orders.
func (s *WatcherStore) GetAllPending(ctx context.Context) ([]*PendingWatcherRecord, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT watcher_id, order_id, user_id, symbol, direction, execution_mode,
			entry_price, stop_loss, tp1_price, tp1_pct, tp2_price, tp2_pct,
			tp3_price, tp3_pct, lot_size, risk_percent, risk_amount, rr_ratio,
			account_balance, sl_distance_pips, pip_value, overshoot_tolerance,
			ltf_confirmed, analysis_id, trading_style, session, grade,
			confluence, confidence, setup_type, created_at
		FROM execution_pending_watchers
		WHERE status = 'PENDING'
		ORDER BY created_at ASC`)
	if err != nil {
		return nil, fmt.Errorf("get all pending watchers: %w", err)
	}
	defer rows.Close()

	var records []*PendingWatcherRecord
	for rows.Next() {
		r := &PendingWatcherRecord{}
		if err := rows.Scan(
			&r.WatcherID, &r.OrderID, &r.UserID, &r.Symbol, &r.Direction,
			&r.ExecutionMode, &r.EntryPrice, &r.StopLoss, &r.TP1Price,
			&r.TP1Pct, &r.TP2Price, &r.TP2Pct, &r.TP3Price, &r.TP3Pct,
			&r.LotSize, &r.RiskPercent, &r.RiskAmount, &r.RRRatio,
			&r.AccountBalance, &r.SLDistancePips, &r.PipValue,
			&r.OvershootTolerance, &r.LTFConfirmed, &r.AnalysisID,
			&r.TradingStyle, &r.Session, &r.Grade, &r.Confluence,
			&r.Confidence, &r.SetupType, &r.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan pending watcher: %w", err)
		}
		records = append(records, r)
	}

	return records, rows.Err()
}
