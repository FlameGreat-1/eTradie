package journal

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// SchemaSQL returns the DDL for the management database tables.
func SchemaSQL() string {
	return `
	CREATE TABLE IF NOT EXISTS management_trades (
		id                BIGSERIAL      PRIMARY KEY,
		trade_id          TEXT           NOT NULL UNIQUE,
		symbol            TEXT           NOT NULL,
		direction         TEXT           NOT NULL,
		entry_price       DOUBLE PRECISION NOT NULL,
		exit_price        DOUBLE PRECISION DEFAULT 0,
		stop_loss         DOUBLE PRECISION NOT NULL,
		initial_sl        DOUBLE PRECISION NOT NULL,
		tp1_price         DOUBLE PRECISION NOT NULL,
		tp2_price         DOUBLE PRECISION NOT NULL,
		tp3_price         DOUBLE PRECISION NOT NULL,
		total_lot_size    DOUBLE PRECISION NOT NULL,
		gross_pnl         DOUBLE PRECISION DEFAULT 0,
		r_multiple        DOUBLE PRECISION DEFAULT 0,
		risk_amount       DOUBLE PRECISION NOT NULL,
		risk_percent      DOUBLE PRECISION NOT NULL,
		confluence_score  DOUBLE PRECISION DEFAULT 0,
		grade             TEXT           NOT NULL,
		setup_type        TEXT           DEFAULT '',
		trading_style     TEXT           NOT NULL,
		session           TEXT           DEFAULT '',
		execution_mode    TEXT           DEFAULT '',
		slippage          DOUBLE PRECISION DEFAULT 0,
		outcome           TEXT           DEFAULT '',
		status            TEXT           NOT NULL DEFAULT 'ACTIVE',
		analysis_id       TEXT           DEFAULT '',
		broker_order_id   TEXT           DEFAULT '',
		opened_at         TIMESTAMPTZ    NOT NULL,
		closed_at         TIMESTAMPTZ,
		duration_minutes  INT            DEFAULT 0,
		sl_adjustments    INT            DEFAULT 0,
		partial_closes    INT            DEFAULT 0,
		created_at        TIMESTAMPTZ    DEFAULT NOW(),
		updated_at        TIMESTAMPTZ    DEFAULT NOW()
	);

	CREATE INDEX IF NOT EXISTS idx_management_trades_status   ON management_trades(status);
	CREATE INDEX IF NOT EXISTS idx_management_trades_symbol   ON management_trades(symbol);
	CREATE INDEX IF NOT EXISTS idx_management_trades_style    ON management_trades(trading_style);
	CREATE INDEX IF NOT EXISTS idx_management_trades_opened   ON management_trades(opened_at);

	CREATE TABLE IF NOT EXISTS management_events (
		id            BIGSERIAL        PRIMARY KEY,
		trade_id      TEXT             NOT NULL REFERENCES management_trades(trade_id),
		event_type    TEXT             NOT NULL,
		symbol        TEXT             NOT NULL,
		price         DOUBLE PRECISION DEFAULT 0,
		new_sl        DOUBLE PRECISION DEFAULT 0,
		closed_volume DOUBLE PRECISION DEFAULT 0,
		realized_pnl  DOUBLE PRECISION DEFAULT 0,
		r_multiple    DOUBLE PRECISION DEFAULT 0,
		reason        TEXT             DEFAULT '',
		timestamp     TIMESTAMPTZ      DEFAULT NOW()
	);

	CREATE INDEX IF NOT EXISTS idx_management_events_trade ON management_events(trade_id);
	`
}

// Repository handles all PostgreSQL operations for the trade journal.
type Repository struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewRepository creates a journal repository.
func NewRepository(pool *pgxpool.Pool) *Repository {
	return &Repository{
		pool: pool,
		log:  observability.Logger("journal"),
	}
}

// InsertTrade persists a new managed trade to the database.
func (r *Repository) InsertTrade(ctx context.Context, t *TradeRecord) error {
	_, err := r.pool.Exec(ctx, `
		INSERT INTO management_trades (
			trade_id, symbol, direction, entry_price, stop_loss, initial_sl,
			tp1_price, tp2_price, tp3_price, total_lot_size,
			risk_amount, risk_percent, confluence_score, grade,
			setup_type, trading_style, session, execution_mode,
			slippage, status, analysis_id, broker_order_id, opened_at
		) VALUES (
			$1, $2, $3, $4, $5, $6,
			$7, $8, $9, $10,
			$11, $12, $13, $14,
			$15, $16, $17, $18,
			$19, $20, $21, $22, $23
		)`,
		t.TradeID, t.Symbol, t.Direction, t.EntryPrice, t.StopLoss, t.InitialSL,
		t.TP1Price, t.TP2Price, t.TP3Price, t.TotalLotSize,
		t.RiskAmount, t.RiskPercent, t.ConfluenceScore, t.Grade,
		t.SetupType, t.TradingStyle, t.Session, t.ExecutionMode,
		t.Slippage, t.Status, t.AnalysisID, t.BrokerOrderID, t.OpenedAt,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("insert trade %s: %w", t.TradeID, err)
	}

	r.log.Info().
		Str("trade_id", t.TradeID).
		Str("symbol", t.Symbol).
		Msg("trade_inserted")
	return nil
}

// InsertEvent records an immutable trade event.
func (r *Repository) InsertEvent(ctx context.Context, e *TradeEvent) error {
	_, err := r.pool.Exec(ctx, `
		INSERT INTO management_events (
			trade_id, event_type, symbol, price, new_sl,
			closed_volume, realized_pnl, r_multiple, reason, timestamp
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
		e.TradeID, e.EventType, e.Symbol, e.Price, e.NewSL,
		e.ClosedVolume, e.RealizedPnL, e.RMultiple, e.Reason, e.Timestamp,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("insert event for trade %s: %w", e.TradeID, err)
	}
	return nil
}

// UpdateTradeClose finalizes a trade when it is fully closed.
func (r *Repository) UpdateTradeClose(ctx context.Context, tradeID string, exitPrice, grossPnL, rMultiple float64, outcome string, closedAt time.Time, durationMinutes, slAdjustments, partialCloses int) error {
	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			exit_price = $2,
			gross_pnl = $3,
			r_multiple = $4,
			outcome = $5,
			status = 'CLOSED',
			closed_at = $6,
			duration_minutes = $7,
			sl_adjustments = $8,
			partial_closes = $9,
			updated_at = NOW()
		WHERE trade_id = $1`,
		tradeID, exitPrice, grossPnL, rMultiple, outcome, closedAt,
		durationMinutes, slAdjustments, partialCloses,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("close trade %s: %w", tradeID, err)
	}

	r.log.Info().
		Str("trade_id", tradeID).
		Str("outcome", outcome).
		Float64("pnl", grossPnL).
		Float64("r", rMultiple).
		Msg("trade_closed")
	return nil
}

// UpdateTradeSL updates the SL and increments the adjustment counter.
func (r *Repository) UpdateTradeSL(ctx context.Context, tradeID string, newSL float64) error {
	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			stop_loss = $2,
			sl_adjustments = sl_adjustments + 1,
			updated_at = NOW()
		WHERE trade_id = $1`,
		tradeID, newSL,
	)
	if err != nil {
		return fmt.Errorf("update SL for trade %s: %w", tradeID, err)
	}
	return nil
}

// UpdateTradePartial records a partial close by incrementing the counter.
func (r *Repository) UpdateTradePartial(ctx context.Context, tradeID string, realizedPnL float64) error {
	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			gross_pnl = gross_pnl + $2,
			partial_closes = partial_closes + 1,
			updated_at = NOW()
		WHERE trade_id = $1`,
		tradeID, realizedPnL,
	)
	if err != nil {
		return fmt.Errorf("update partial for trade %s: %w", tradeID, err)
	}
	return nil
}

// GetActiveTrades returns all trades with status ACTIVE.
func (r *Repository) GetActiveTrades(ctx context.Context) ([]*TradeRecord, error) {
	rows, err := r.pool.Query(ctx, `
		SELECT trade_id, symbol, direction, entry_price, stop_loss, initial_sl,
			tp1_price, tp2_price, tp3_price, total_lot_size,
			risk_amount, risk_percent, confluence_score, grade,
			setup_type, trading_style, session, execution_mode,
			slippage, status, analysis_id, broker_order_id, opened_at
		FROM management_trades
		WHERE status != 'CLOSED'
		ORDER BY opened_at ASC`)
	if err != nil {
		return nil, fmt.Errorf("get active trades: %w", err)
	}
	defer rows.Close()

	var trades []*TradeRecord
	for rows.Next() {
		t := &TradeRecord{}
		if err := rows.Scan(
			&t.TradeID, &t.Symbol, &t.Direction, &t.EntryPrice, &t.StopLoss, &t.InitialSL,
			&t.TP1Price, &t.TP2Price, &t.TP3Price, &t.TotalLotSize,
			&t.RiskAmount, &t.RiskPercent, &t.ConfluenceScore, &t.Grade,
			&t.SetupType, &t.TradingStyle, &t.Session, &t.ExecutionMode,
			&t.Slippage, &t.Status, &t.AnalysisID, &t.BrokerOrderID, &t.OpenedAt,
		); err != nil {
			return nil, fmt.Errorf("scan active trade: %w", err)
		}
		trades = append(trades, t)
	}

	return trades, nil
}

// GetClosedTrades returns closed trades with pagination and optional filters.
func (r *Repository) GetClosedTrades(ctx context.Context, limit, offset int, symbolFilter, styleFilter string) ([]*TradeRecord, int, error) {
	// Build WHERE clause dynamically.
	where := "WHERE status = 'CLOSED'"
	args := []interface{}{}
	argIdx := 1

	if symbolFilter != "" {
		where += fmt.Sprintf(" AND symbol = $%d", argIdx)
		args = append(args, symbolFilter)
		argIdx++
	}
	if styleFilter != "" {
		where += fmt.Sprintf(" AND trading_style = $%d", argIdx)
		args = append(args, styleFilter)
		argIdx++
	}

	// Get total count.
	var total int
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM management_trades %s", where)
	if err := r.pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("count closed trades: %w", err)
	}

	// Get paginated results.
	if limit <= 0 {
		limit = 50
	}
	query := fmt.Sprintf(`
		SELECT trade_id, symbol, direction, entry_price, exit_price, stop_loss,
			total_lot_size, gross_pnl, r_multiple, confluence_score, grade,
			setup_type, trading_style, outcome, opened_at, closed_at,
			duration_minutes, sl_adjustments, partial_closes, analysis_id
		FROM management_trades
		%s
		ORDER BY closed_at DESC
		LIMIT $%d OFFSET $%d`, where, argIdx, argIdx+1)
	args = append(args, limit, offset)

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("get closed trades: %w", err)
	}
	defer rows.Close()

	var trades []*TradeRecord
	for rows.Next() {
		t := &TradeRecord{}
		if err := rows.Scan(
			&t.TradeID, &t.Symbol, &t.Direction, &t.EntryPrice, &t.ExitPrice, &t.StopLoss,
			&t.TotalLotSize, &t.GrossPnL, &t.RMultiple, &t.ConfluenceScore, &t.Grade,
			&t.SetupType, &t.TradingStyle, &t.Outcome, &t.OpenedAt, &t.ClosedAt,
			&t.DurationMinutes, &t.SLAdjustments, &t.PartialCloses, &t.AnalysisID,
		); err != nil {
			return nil, 0, fmt.Errorf("scan closed trade: %w", err)
		}
		trades = append(trades, t)
	}

	return trades, total, nil
}
