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
// All tables include a user_id column for multi-tenant data isolation.
// Uses IF NOT EXISTS for idempotent re-runs.
//
// The managed-trade row is a COMPLETE snapshot of the in-memory Trade so a
// fresh process can fully resume on restart (audit EM-C1/EM-C2): the TP split
// percentages, broker point/digits, R:R, remaining open volume, and runtime
// flags (tp*_hit, breakeven_set) are all persisted.
func SchemaSQL() string {
	return `
	DO $$ BEGIN
		IF NOT EXISTS (
			SELECT 1 FROM information_schema.columns
			WHERE table_name = 'management_trades' AND column_name = 'user_id'
		) THEN
			IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'management_trades') THEN
				ALTER TABLE management_trades ADD COLUMN user_id VARCHAR(64);
				UPDATE management_trades SET user_id = 'system' WHERE user_id IS NULL;
				ALTER TABLE management_trades ALTER COLUMN user_id SET NOT NULL;
			END IF;
		END IF;
	END $$;

	CREATE TABLE IF NOT EXISTS management_trades (
		id                 BIGSERIAL      PRIMARY KEY,
		user_id            VARCHAR(64)    NOT NULL,
		trade_id           TEXT           NOT NULL UNIQUE,
		symbol             TEXT           NOT NULL,
		direction          TEXT           NOT NULL,
		entry_price        DOUBLE PRECISION NOT NULL,
		exit_price         DOUBLE PRECISION DEFAULT 0,
		stop_loss          DOUBLE PRECISION NOT NULL,
		initial_sl         DOUBLE PRECISION NOT NULL,
		tp1_price          DOUBLE PRECISION NOT NULL,
		tp1_pct            INT            NOT NULL DEFAULT 0,
		tp2_price          DOUBLE PRECISION NOT NULL,
		tp2_pct            INT            NOT NULL DEFAULT 0,
		tp3_price          DOUBLE PRECISION NOT NULL,
		tp3_pct            INT            NOT NULL DEFAULT 0,
		total_lot_size     DOUBLE PRECISION NOT NULL,
		remaining_lot_size DOUBLE PRECISION NOT NULL DEFAULT 0,
		point              DOUBLE PRECISION NOT NULL DEFAULT 0,
		digits             INT            NOT NULL DEFAULT 0,
		rr_ratio           DOUBLE PRECISION NOT NULL DEFAULT 0,
		gross_pnl          DOUBLE PRECISION DEFAULT 0,
		r_multiple         DOUBLE PRECISION DEFAULT 0,
		risk_amount        DOUBLE PRECISION NOT NULL,
		risk_percent       DOUBLE PRECISION NOT NULL,
		confluence_score   DOUBLE PRECISION DEFAULT 0,
		grade              TEXT           NOT NULL,
		setup_type         TEXT           DEFAULT '',
		trading_style      TEXT           NOT NULL,
		session            TEXT           DEFAULT '',
		execution_mode     TEXT           DEFAULT '',
		slippage           DOUBLE PRECISION DEFAULT 0,
		tp1_hit            BOOLEAN        NOT NULL DEFAULT FALSE,
		tp2_hit            BOOLEAN        NOT NULL DEFAULT FALSE,
		tp3_hit            BOOLEAN        NOT NULL DEFAULT FALSE,
		breakeven_set      BOOLEAN        NOT NULL DEFAULT FALSE,
		outcome            TEXT           DEFAULT '',
		status             TEXT           NOT NULL DEFAULT 'ACTIVE',
		analysis_id        TEXT           DEFAULT '',
		broker_order_id    TEXT           DEFAULT '',
		opened_at          TIMESTAMPTZ    NOT NULL,
		closed_at          TIMESTAMPTZ,
		duration_minutes   INT            DEFAULT 0,
		sl_adjustments     INT            DEFAULT 0,
		partial_closes     INT            DEFAULT 0,
		created_at         TIMESTAMPTZ    DEFAULT NOW(),
		updated_at         TIMESTAMPTZ    DEFAULT NOW()
	);

	-- Idempotent column additions for pre-existing deployments (audit EM-C1/C2).
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp1_pct            INT              NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp2_pct            INT              NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp3_pct            INT              NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS remaining_lot_size DOUBLE PRECISION NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS point              DOUBLE PRECISION NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS digits             INT              NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS rr_ratio           DOUBLE PRECISION NOT NULL DEFAULT 0;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp1_hit            BOOLEAN          NOT NULL DEFAULT FALSE;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp2_hit            BOOLEAN          NOT NULL DEFAULT FALSE;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS tp3_hit            BOOLEAN          NOT NULL DEFAULT FALSE;
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS breakeven_set      BOOLEAN          NOT NULL DEFAULT FALSE;

	-- Typed provenance discriminator for the manual trading-plan journal
	-- (distinct from grade). Idempotent add + one-time backfill from the
	-- pre-existing grade convention so historical rows classify correctly.
	ALTER TABLE management_trades ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'SYSTEM';

	UPDATE management_trades
	   SET origin = CASE
	       WHEN grade LIKE 'MANUAL/RECONCILED%' THEN 'MANUAL_RECONCILED'
	       WHEN grade LIKE 'MANUAL/RESTORED%'   THEN 'MANUAL_RESTORED'
	       ELSE 'SYSTEM'
	   END
	 WHERE origin = 'SYSTEM'
	   AND grade LIKE 'MANUAL/%';

	UPDATE management_trades
	   SET remaining_lot_size = total_lot_size
	 WHERE status != 'CLOSED' AND remaining_lot_size = 0 AND total_lot_size > 0;

	CREATE INDEX IF NOT EXISTS idx_management_trades_user_id  ON management_trades(user_id);
	CREATE INDEX IF NOT EXISTS idx_management_trades_status   ON management_trades(status);
	CREATE INDEX IF NOT EXISTS idx_management_trades_symbol   ON management_trades(symbol);
	CREATE INDEX IF NOT EXISTS idx_management_trades_style    ON management_trades(trading_style);
	CREATE INDEX IF NOT EXISTS idx_management_trades_opened   ON management_trades(opened_at);
	CREATE INDEX IF NOT EXISTS idx_management_trades_user_status ON management_trades(user_id, status);
	CREATE INDEX IF NOT EXISTS idx_management_trades_user_origin_status ON management_trades(user_id, origin, status);

	DO $$ BEGIN
		IF NOT EXISTS (
			SELECT 1 FROM information_schema.columns
			WHERE table_name = 'management_events' AND column_name = 'user_id'
		) THEN
			IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'management_events') THEN
				ALTER TABLE management_events ADD COLUMN user_id VARCHAR(64);
				UPDATE management_events SET user_id = 'system' WHERE user_id IS NULL;
				ALTER TABLE management_events ALTER COLUMN user_id SET NOT NULL;
			END IF;
		END IF;
	END $$;

	CREATE TABLE IF NOT EXISTS management_events (
		id            BIGSERIAL        PRIMARY KEY,
		user_id       VARCHAR(64)      NOT NULL,
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

	CREATE INDEX IF NOT EXISTS idx_management_events_trade   ON management_events(trade_id);
	CREATE INDEX IF NOT EXISTS idx_management_events_user_id ON management_events(user_id);
	`
}

// Repository handles all PostgreSQL operations for the trade journal.
// All queries are scoped by user_id for multi-tenant data isolation.
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

// tradeSelectColumns is the canonical ordered column list for reading a full
// managed-trade snapshot. Kept in one place so every SELECT and its Scan stay
// in lockstep (avoids column/scan drift on the money-bearing row).
const tradeSelectColumns = `
	user_id, trade_id, symbol, direction, entry_price, stop_loss, initial_sl,
	tp1_price, tp1_pct, tp2_price, tp2_pct, tp3_price, tp3_pct,
	total_lot_size, remaining_lot_size, point, digits, rr_ratio,
	risk_amount, risk_percent, confluence_score, grade,
	setup_type, trading_style, session, execution_mode,
	slippage, tp1_hit, tp2_hit, tp3_hit, breakeven_set,
	origin, status, analysis_id, broker_order_id, opened_at`

// rowScanner is satisfied by both pgx.Row and pgx.Rows.
type rowScanner interface {
	Scan(dest ...any) error
}

// scanTrade scans a row produced by a SELECT of tradeSelectColumns.
func scanTrade(row rowScanner) (*TradeRecord, error) {
	t := &TradeRecord{}
	err := row.Scan(
		&t.UserID, &t.TradeID, &t.Symbol, &t.Direction, &t.EntryPrice, &t.StopLoss, &t.InitialSL,
		&t.TP1Price, &t.TP1Pct, &t.TP2Price, &t.TP2Pct, &t.TP3Price, &t.TP3Pct,
		&t.TotalLotSize, &t.RemainingLotSize, &t.Point, &t.Digits, &t.RRRatio,
		&t.RiskAmount, &t.RiskPercent, &t.ConfluenceScore, &t.Grade,
		&t.SetupType, &t.TradingStyle, &t.Session, &t.ExecutionMode,
		&t.Slippage, &t.TP1Hit, &t.TP2Hit, &t.TP3Hit, &t.BreakevenSet,
		&t.Origin, &t.Status, &t.AnalysisID, &t.BrokerOrderID, &t.OpenedAt,
	)
	if err != nil {
		return nil, err
	}
	return t, nil
}

// InsertTrade persists a new managed trade to the database.
func (r *Repository) InsertTrade(ctx context.Context, t *TradeRecord) error {
	if t.UserID == "" {
		return fmt.Errorf("insert trade %s: user_id must not be empty", t.TradeID)
	}
	// Default a blank origin to SYSTEM so any caller that has not been
	// updated to set it explicitly still produces a correctly-typed row.
	origin := t.Origin
	if origin == "" {
		origin = OriginSystem
	}

	_, err := r.pool.Exec(ctx, `
		INSERT INTO management_trades (
			user_id, trade_id, symbol, direction, entry_price, stop_loss, initial_sl,
			tp1_price, tp1_pct, tp2_price, tp2_pct, tp3_price, tp3_pct,
			total_lot_size, remaining_lot_size, point, digits, rr_ratio,
			risk_amount, risk_percent, confluence_score, grade,
			setup_type, trading_style, session, execution_mode,
			slippage, tp1_hit, tp2_hit, tp3_hit, breakeven_set,
			origin, status, analysis_id, broker_order_id, opened_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7,
			$8, $9, $10, $11, $12, $13,
			$14, $15, $16, $17, $18,
			$19, $20, $21, $22,
			$23, $24, $25, $26,
			$27, $28, $29, $30, $31,
			$32, $33, $34, $35, $36
		)`,
		t.UserID, t.TradeID, t.Symbol, t.Direction, t.EntryPrice, t.StopLoss, t.InitialSL,
		t.TP1Price, t.TP1Pct, t.TP2Price, t.TP2Pct, t.TP3Price, t.TP3Pct,
		t.TotalLotSize, t.RemainingLotSize, t.Point, t.Digits, t.RRRatio,
		t.RiskAmount, t.RiskPercent, t.ConfluenceScore, t.Grade,
		t.SetupType, t.TradingStyle, t.Session, t.ExecutionMode,
		t.Slippage, t.TP1Hit, t.TP2Hit, t.TP3Hit, t.BreakevenSet,
		origin, t.Status, t.AnalysisID, t.BrokerOrderID, t.OpenedAt,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("insert trade %s: %w", t.TradeID, err)
	}

	r.log.Info().
		Str("trade_id", t.TradeID).
		Str("user_id", t.UserID).
		Str("symbol", t.Symbol).
		Msg("trade_inserted")
	return nil
}

// InsertEvent records an immutable trade event.
func (r *Repository) InsertEvent(ctx context.Context, e *TradeEvent) error {
	if e.UserID == "" {
		return fmt.Errorf("insert event for trade %s: user_id must not be empty", e.TradeID)
	}

	_, err := r.pool.Exec(ctx, `
		INSERT INTO management_events (
			user_id, trade_id, event_type, symbol, price, new_sl,
			closed_volume, realized_pnl, r_multiple, reason, timestamp
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
		e.UserID, e.TradeID, e.EventType, e.Symbol, e.Price, e.NewSL,
		e.ClosedVolume, e.RealizedPnL, e.RMultiple, e.Reason, e.Timestamp,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("insert event for trade %s: %w", e.TradeID, err)
	}
	return nil
}

// UpdateTradeClose finalizes a trade when it is fully closed.
func (r *Repository) UpdateTradeClose(ctx context.Context, userID, tradeID string, exitPrice, grossPnL, rMultiple float64, outcome string, closedAt time.Time, durationMinutes, slAdjustments, partialCloses int) error {
	if userID == "" {
		return fmt.Errorf("close trade %s: user_id must not be empty", tradeID)
	}

	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			exit_price = $3,
			gross_pnl = $4,
			r_multiple = $5,
			outcome = $6,
			status = 'CLOSED',
			remaining_lot_size = 0,
			closed_at = $7,
			duration_minutes = $8,
			sl_adjustments = $9,
			partial_closes = $10,
			updated_at = NOW()
		WHERE trade_id = $1 AND user_id = $2`,
		tradeID, userID, exitPrice, grossPnL, rMultiple, outcome, closedAt,
		durationMinutes, slAdjustments, partialCloses,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("close trade %s: %w", tradeID, err)
	}

	r.log.Info().
		Str("trade_id", tradeID).
		Str("user_id", userID).
		Str("outcome", outcome).
		Float64("pnl", grossPnL).
		Float64("r", rMultiple).
		Msg("trade_closed")
	return nil
}

// UpdateTradeSL updates the SL and increments the adjustment counter.
func (r *Repository) UpdateTradeSL(ctx context.Context, userID, tradeID string, newSL float64) error {
	if userID == "" {
		return fmt.Errorf("update SL for trade %s: user_id must not be empty", tradeID)
	}

	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			stop_loss = $3,
			sl_adjustments = sl_adjustments + 1,
			updated_at = NOW()
		WHERE trade_id = $1 AND user_id = $2`,
		tradeID, userID, newSL,
	)
	if err != nil {
		return fmt.Errorf("update SL for trade %s: %w", tradeID, err)
	}
	return nil
}

// UpdateTradeRuntime persists the worker-mutated runtime state of an active
// trade so a restart can resume EXACTLY where the worker left off (audit
// EM-C1/EM-C2): remaining open volume, TP-hit flags, break-even flag, and the
// current SL. Scoped by user_id. Counters/status are owned by
// UpdateTradePartial / UpdateTradeClose / UpdateTradeSL.
func (r *Repository) UpdateTradeRuntime(ctx context.Context, userID, tradeID string, remainingLot, stopLoss float64, tp1Hit, tp2Hit, tp3Hit, breakevenSet bool) error {
	if userID == "" {
		return fmt.Errorf("update runtime for trade %s: user_id must not be empty", tradeID)
	}

	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			remaining_lot_size = $3,
			stop_loss = $4,
			tp1_hit = $5,
			tp2_hit = $6,
			tp3_hit = $7,
			breakeven_set = $8,
			updated_at = NOW()
		WHERE trade_id = $1 AND user_id = $2`,
		tradeID, userID, remainingLot, stopLoss, tp1Hit, tp2Hit, tp3Hit, breakevenSet,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("update runtime for trade %s: %w", tradeID, err)
	}
	return nil
}

// UpdateTradePointDigits persists a self-healed broker point/digits onto
// the managed-trade row so the heal survives the next restart (audit
// EM-C2). Scoped by user_id. A non-positive point is ignored to avoid
// overwriting a good value with a bad fetch.
func (r *Repository) UpdateTradePointDigits(ctx context.Context, userID, tradeID string, point float64, digits int) error {
	if userID == "" {
		return fmt.Errorf("update point/digits for trade %s: user_id must not be empty", tradeID)
	}
	if point <= 0 {
		return nil
	}

	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			point = $3,
			digits = $4,
			updated_at = NOW()
		WHERE trade_id = $1 AND user_id = $2`,
		tradeID, userID, point, digits,
	)
	if err != nil {
		observability.JournalWriteFailures.Inc()
		return fmt.Errorf("update point/digits for trade %s: %w", tradeID, err)
	}
	return nil
}

// UpdateTradePartial records a partial close by incrementing the counter.
func (r *Repository) UpdateTradePartial(ctx context.Context, userID, tradeID string, realizedPnL float64) error {
	if userID == "" {
		return fmt.Errorf("update partial for trade %s: user_id must not be empty", tradeID)
	}

	_, err := r.pool.Exec(ctx, `
		UPDATE management_trades SET
			gross_pnl = gross_pnl + $3,
			partial_closes = partial_closes + 1,
			updated_at = NOW()
		WHERE trade_id = $1 AND user_id = $2`,
		tradeID, userID, realizedPnL,
	)
	if err != nil {
		return fmt.Errorf("update partial for trade %s: %w", tradeID, err)
	}
	return nil
}

// GetTradeByBrokerOrderID returns a trade by its broker order ID (MT5 ticket).
func (r *Repository) GetTradeByBrokerOrderID(ctx context.Context, userID, brokerOrderID string) (*TradeRecord, error) {
	if brokerOrderID == "" {
		return nil, nil
	}
	if userID == "" {
		return nil, fmt.Errorf("get trade by broker order ID %s: user_id must not be empty", brokerOrderID)
	}

	row := r.pool.QueryRow(ctx, `
		SELECT `+tradeSelectColumns+`
		FROM management_trades
		WHERE broker_order_id = $1 AND user_id = $2 LIMIT 1`, brokerOrderID, userID)

	t, err := scanTrade(row)
	if err != nil {
		return nil, nil // return nil if not found
	}
	return t, nil
}

// GetActiveTrades returns all non-closed trades for a specific user.
func (r *Repository) GetActiveTrades(ctx context.Context, userID string) ([]*TradeRecord, error) {
	if userID == "" {
		return nil, fmt.Errorf("get active trades: user_id must not be empty")
	}

	rows, err := r.pool.Query(ctx, `
		SELECT `+tradeSelectColumns+`
		FROM management_trades
		WHERE status != 'CLOSED' AND user_id = $1
		ORDER BY opened_at ASC`, userID)
	if err != nil {
		return nil, fmt.Errorf("get active trades: %w", err)
	}
	defer rows.Close()

	var trades []*TradeRecord
	for rows.Next() {
		t, err := scanTrade(rows)
		if err != nil {
			return nil, fmt.Errorf("scan active trade: %w", err)
		}
		trades = append(trades, t)
	}
	return trades, nil
}

// GetAllActiveTrades returns all non-closed trades across ALL users.
func (r *Repository) GetAllActiveTrades(ctx context.Context) ([]*TradeRecord, error) {
	rows, err := r.pool.Query(ctx, `
		SELECT `+tradeSelectColumns+`
		FROM management_trades
		WHERE status != 'CLOSED'
		ORDER BY opened_at ASC`)
	if err != nil {
		return nil, fmt.Errorf("get all active trades: %w", err)
	}
	defer rows.Close()

	var trades []*TradeRecord
	for rows.Next() {
		t, err := scanTrade(rows)
		if err != nil {
			return nil, fmt.Errorf("scan active trade: %w", err)
		}
		trades = append(trades, t)
	}
	return trades, nil
}

// GetClosedTrades returns closed trades with pagination and optional filters.
func (r *Repository) GetClosedTrades(ctx context.Context, userID string, limit, offset int, symbolFilter, styleFilter string) ([]*TradeRecord, int, error) {
	if userID == "" {
		return nil, 0, fmt.Errorf("get closed trades: user_id must not be empty")
	}

	where := "WHERE status = 'CLOSED' AND user_id = $1"
	args := []interface{}{userID}
	argIdx := 2

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

	var total int
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM management_trades %s", where)
	if err := r.pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("count closed trades: %w", err)
	}

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
		t.UserID = userID
		trades = append(trades, t)
	}

	return trades, total, nil
}

// DailyPnL holds the aggregated P&L for a single calendar day.
type DailyPnL struct {
	Date string  `db:"day"`
	PnL  float64 `db:"pnl"`
}

// StreakInfo holds the current and max consecutive profitable-day streaks.
type StreakInfo struct {
	CurrentStreak int
	MaxStreak     int
}

// GetDailyPnL returns the sum of gross_pnl grouped by the calendar day
// the trade was closed, for a specific month.
func (r *Repository) GetDailyPnL(ctx context.Context, userID string, year, month int, tz string) ([]DailyPnL, error) {
	if userID == "" {
		return nil, fmt.Errorf("get daily pnl: user_id must not be empty")
	}

	query := `
		SELECT
			TO_CHAR(closed_at AT TIME ZONE $4, 'YYYY-MM-DD') AS day,
			SUM(gross_pnl) AS pnl
		FROM management_trades
		WHERE status = 'CLOSED'
		  AND user_id = $1
		  AND EXTRACT(YEAR FROM closed_at AT TIME ZONE $4) = $2
		  AND EXTRACT(MONTH FROM closed_at AT TIME ZONE $4) = $3
		GROUP BY day
		ORDER BY day`

	rows, err := r.pool.Query(ctx, query, userID, year, month, tz)
	if err != nil {
		return nil, fmt.Errorf("get daily pnl: %w", err)
	}
	defer rows.Close()

	var results []DailyPnL
	for rows.Next() {
		var d DailyPnL
		if err := rows.Scan(&d.Date, &d.PnL); err != nil {
			return nil, fmt.Errorf("scan daily pnl: %w", err)
		}
		results = append(results, d)
	}

	return results, nil
}

// GetStreaks calculates the current and all-time max consecutive
// profitable-day streaks using a CTE.
func (r *Repository) GetStreaks(ctx context.Context, userID, tz string) (*StreakInfo, error) {
	if userID == "" {
		return nil, fmt.Errorf("get streaks: user_id must not be empty")
	}

	query := `
		WITH daily AS (
			SELECT
				(closed_at AT TIME ZONE $2)::date AS day,
				SUM(gross_pnl) AS pnl
			FROM management_trades
			WHERE status = 'CLOSED' AND user_id = $1
			GROUP BY day
			ORDER BY day
		),
		flagged AS (
			SELECT day, pnl,
				CASE WHEN pnl > 0 THEN 1 ELSE 0 END AS is_win,
				ROW_NUMBER() OVER (ORDER BY day)
				- ROW_NUMBER() OVER (
					PARTITION BY CASE WHEN pnl > 0 THEN 1 ELSE 0 END
					ORDER BY day
				  ) AS grp
			FROM daily
		),
		streaks AS (
			SELECT grp, MIN(day) AS streak_start, MAX(day) AS streak_end,
				COUNT(*) AS streak_len, is_win
			FROM flagged
			WHERE is_win = 1
			GROUP BY grp, is_win
		)
		SELECT
			COALESCE(
				(SELECT streak_len FROM streaks
				 WHERE streak_end = (SELECT MAX(day) FROM daily WHERE pnl > 0)
				   AND streak_end >= (SELECT MAX(day) FROM daily)
				 LIMIT 1), 0
			) AS current_streak,
			COALESCE((SELECT MAX(streak_len) FROM streaks), 0) AS max_streak`

	var info StreakInfo
	err := r.pool.QueryRow(ctx, query, userID, tz).Scan(&info.CurrentStreak, &info.MaxStreak)
	if err != nil {
		return &StreakInfo{}, nil
	}

	return &info, nil
}