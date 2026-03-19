package analytics

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/management/internal/observability"
)

// Metrics calculates real-time performance analytics from the journal
// database. Used by the GetPerformanceMetrics gRPC endpoint and the
// dashboard.
type Metrics struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewMetrics creates a performance metrics calculator.
func NewMetrics(pool *pgxpool.Pool) *Metrics {
	return &Metrics{
		pool: pool,
		log:  observability.Logger("analytics"),
	}
}

// PerformanceSummary holds aggregated performance data.
type PerformanceSummary struct {
	WinRate              float64
	AvgRMultiple         float64
	Expectancy           float64
	TotalTrades          int
	Wins                 int
	Losses               int
	Breakevens           int
	TotalPnL             float64
	MaxConsecutiveWins   int
	MaxConsecutiveLosses int
	MaxDrawdownPct       float64
	BestTradeR           float64
	WorstTradeR          float64
	WinRateBySymbol      map[string]float64
	WinRateByStyle       map[string]float64
	WinRateBySetup       map[string]float64
	WinRateBySession     map[string]float64
}

// Calculate computes the full performance summary for a given period filter.
func (m *Metrics) Calculate(ctx context.Context, period string) (*PerformanceSummary, error) {
	summary := &PerformanceSummary{
		WinRateBySymbol:  make(map[string]float64),
		WinRateByStyle:   make(map[string]float64),
		WinRateBySetup:   make(map[string]float64),
		WinRateBySession: make(map[string]float64),
	}

	// Build period filter.
	periodFilter := ""
	switch period {
	case "DAILY":
		periodFilter = "AND closed_at >= CURRENT_DATE"
	case "WEEKLY":
		periodFilter = "AND closed_at >= DATE_TRUNC('week', CURRENT_DATE)"
	case "MONTHLY":
		periodFilter = "AND closed_at >= DATE_TRUNC('month', CURRENT_DATE)"
	default:
		// ALL_TIME — no filter.
	}

	// Core stats.
	coreQuery := `
		SELECT
			COUNT(*) as total,
			COUNT(*) FILTER (WHERE outcome = 'WIN') as wins,
			COUNT(*) FILTER (WHERE outcome = 'LOSS') as losses,
			COUNT(*) FILTER (WHERE outcome = 'BREAKEVEN') as breakevens,
			COALESCE(SUM(gross_pnl), 0) as total_pnl,
			COALESCE(AVG(r_multiple), 0) as avg_r,
			COALESCE(MAX(r_multiple), 0) as best_r,
			COALESCE(MIN(r_multiple), 0) as worst_r
		FROM management_trades
		WHERE status = 'CLOSED' ` + periodFilter

	err := m.pool.QueryRow(ctx, coreQuery).Scan(
		&summary.TotalTrades,
		&summary.Wins,
		&summary.Losses,
		&summary.Breakevens,
		&summary.TotalPnL,
		&summary.AvgRMultiple,
		&summary.BestTradeR,
		&summary.WorstTradeR,
	)
	if err != nil {
		return nil, err
	}

	// Win rate.
	if summary.TotalTrades > 0 {
		summary.WinRate = float64(summary.Wins) / float64(summary.TotalTrades) * 100.0
	}

	// Expectancy = (WinRate * AvgWin) - (LossRate * AvgLoss).
	if summary.TotalTrades > 0 {
		var avgWinR, avgLossR float64
		statsQuery := `
			SELECT
				COALESCE(AVG(r_multiple) FILTER (WHERE outcome = 'WIN'), 0),
				COALESCE(ABS(AVG(r_multiple) FILTER (WHERE outcome = 'LOSS')), 0)
			FROM management_trades
			WHERE status = 'CLOSED' ` + periodFilter
		if err := m.pool.QueryRow(ctx, statsQuery).Scan(&avgWinR, &avgLossR); err == nil {
			winRate := float64(summary.Wins) / float64(summary.TotalTrades)
			lossRate := float64(summary.Losses) / float64(summary.TotalTrades)
			summary.Expectancy = (winRate * avgWinR) - (lossRate * avgLossR)
		}
	}

	// Consecutive streaks.
	summary.MaxConsecutiveWins, summary.MaxConsecutiveLosses = m.calculateStreaks(ctx, periodFilter)

	// Win rate breakdowns by dimension.
	summary.WinRateBySymbol = m.winRateByDimension(ctx, "symbol", periodFilter)
	summary.WinRateByStyle = m.winRateByDimension(ctx, "trading_style", periodFilter)
	summary.WinRateBySetup = m.winRateByDimension(ctx, "setup_type", periodFilter)
	summary.WinRateBySession = m.winRateByDimension(ctx, "session", periodFilter)

	return summary, nil
}

func (m *Metrics) calculateStreaks(ctx context.Context, periodFilter string) (maxWins, maxLosses int) {
	rows, err := m.pool.Query(ctx, `
		SELECT outcome FROM management_trades
		WHERE status = 'CLOSED' `+periodFilter+`
		ORDER BY closed_at ASC`)
	if err != nil {
		return 0, 0
	}
	defer rows.Close()

	currentWins, currentLosses := 0, 0
	for rows.Next() {
		var outcome string
		if err := rows.Scan(&outcome); err != nil {
			continue
		}
		switch outcome {
		case "WIN":
			currentWins++
			currentLosses = 0
			if currentWins > maxWins {
				maxWins = currentWins
			}
		case "LOSS":
			currentLosses++
			currentWins = 0
			if currentLosses > maxLosses {
				maxLosses = currentLosses
			}
		default:
			currentWins = 0
			currentLosses = 0
		}
	}
	return maxWins, maxLosses
}

func (m *Metrics) winRateByDimension(ctx context.Context, dimension, periodFilter string) map[string]float64 {
	result := make(map[string]float64)

	query := `
		SELECT ` + dimension + `,
			COUNT(*) FILTER (WHERE outcome = 'WIN')::float / NULLIF(COUNT(*), 0) * 100 as win_rate
		FROM management_trades
		WHERE status = 'CLOSED' AND ` + dimension + ` != '' ` + periodFilter + `
		GROUP BY ` + dimension

	rows, err := m.pool.Query(ctx, query)
	if err != nil {
		return result
	}
	defer rows.Close()

	for rows.Next() {
		var key string
		var rate float64
		if err := rows.Scan(&key, &rate); err != nil {
			continue
		}
		result[key] = rate
	}
	return result
}
