package analytics

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// PerformanceAggregator produces the rich, deterministic per-user
// bundle the engine's performance-review LLM consumes.
//
// Why a dedicated aggregator (not Metrics.Calculate):
//   - Metrics is built for the live dashboard: aggregate roll-ups
//     only, no per-trade rows.
//   - The review LLM needs both the deterministic aggregates AND a
//     bounded sample of trade-level rows so it can quote specific
//     setups, sessions, and risk events when writing the narrative.
//   - The aggregator carries a confidence band per PLAN.md §11 so
//     the LLM cannot fabricate precision on a sparse sample.
//
// All queries are scoped by user_id and bounded by [period_start,
// period_end] (closed-inclusive). Nothing here mutates rows.
type PerformanceAggregator struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewPerformanceAggregator creates a new aggregator backed by the
// management Postgres pool.
func NewPerformanceAggregator(pool *pgxpool.Pool) *PerformanceAggregator {
	return &PerformanceAggregator{
		pool: pool,
		log:  observability.Logger("perf_aggregator"),
	}
}

// MaxTradeRowsForLLM caps the per-trade slice we forward to the LLM.
// 200 rows of ~25 fields each is ~50 KB of JSON — well under any
// model's context budget while still letting the LLM cite specific
// trades. Aggregate roll-ups capture everything beyond this slice.
const MaxTradeRowsForLLM = 200

// Confidence thresholds (mirrors performancereview.ConfidenceBand).
const (
	confHighMinTrades   = 20
	confMediumMinTrades = 8
	confLowMinTrades    = 3
)

// Bundle is the full per-window aggregation returned to the engine.
// JSON tags use snake_case; the engine model mirrors this shape
// field-for-field in PerformanceReviewBundle.
type Bundle struct {
	UserID      string    `json:"user_id"`
	Period      string    `json:"period"`
	PeriodStart time.Time `json:"period_start"`
	PeriodEnd   time.Time `json:"period_end"`

	Summary    Summary       `json:"summary"`
	BySession  []DimensionRow `json:"by_session"`
	BySetup    []DimensionRow `json:"by_setup"`
	ByStyle    []DimensionRow `json:"by_style"`
	ByGrade    []DimensionRow `json:"by_grade"`
	BySymbol   []DimensionRow `json:"by_symbol"`
	ByDayOfWeek []DimensionRow `json:"by_day_of_week"`
	ByHourOfDay []DimensionRow `json:"by_hour_of_day"`

	Risk       Risk          `json:"risk"`
	Adherence  Adherence     `json:"adherence"`
	Behavior   Behavior      `json:"behavior"`
	Trades     []TradeRow    `json:"trades"`

	Confidence Confidence    `json:"confidence"`
}

// Summary holds the window-level aggregates.
type Summary struct {
	TotalTrades          int     `json:"total_trades"`
	Wins                 int     `json:"wins"`
	Losses               int     `json:"losses"`
	Breakevens           int     `json:"breakevens"`
	WinRatePct           float64 `json:"win_rate_pct"`
	LossRatePct          float64 `json:"loss_rate_pct"`
	GrossPnL             float64 `json:"gross_pnl"`
	AvgRMultiple         float64 `json:"avg_r_multiple"`
	BestRMultiple        float64 `json:"best_r_multiple"`
	WorstRMultiple       float64 `json:"worst_r_multiple"`
	Expectancy           float64 `json:"expectancy"`
	MaxConsecutiveWins   int     `json:"max_consecutive_wins"`
	MaxConsecutiveLosses int     `json:"max_consecutive_losses"`
	AvgDurationMinutes   float64 `json:"avg_duration_minutes"`
	DistinctSymbols      int     `json:"distinct_symbols"`
	DistinctSetups       int     `json:"distinct_setups"`
}

// DimensionRow is one bucket on a per-dimension breakdown (e.g. one
// session, one setup, one trading style).
type DimensionRow struct {
	Key         string  `json:"key"`
	Trades      int     `json:"trades"`
	Wins        int     `json:"wins"`
	Losses      int     `json:"losses"`
	WinRatePct  float64 `json:"win_rate_pct"`
	AvgR        float64 `json:"avg_r"`
	PnL         float64 `json:"pnl"`
}

// Risk is the risk-discipline view (PLAN.md §8).
type Risk struct {
	AvgRiskPercent       float64 `json:"avg_risk_percent"`
	MaxRiskPercent       float64 `json:"max_risk_percent"`
	TradesOverOnePct     int     `json:"trades_over_one_pct"`
	TradesOverOneHalfPct int     `json:"trades_over_one_half_pct"`
	TradesOverTwoPct     int     `json:"trades_over_two_pct"`
	WorstSingleTradePnL  float64 `json:"worst_single_trade_pnl"`
}

// Adherence is the rule-compliance view (PLAN.md §4, §13).
type Adherence struct {
	TotalSLAdjustments  int     `json:"total_sl_adjustments"`
	AvgSLAdjustments    float64 `json:"avg_sl_adjustments_per_trade"`
	TradesWithSLMoved   int     `json:"trades_with_sl_moved"`
	TotalPartialCloses  int     `json:"total_partial_closes"`
	TradesWithPartials  int     `json:"trades_with_partials"`
}

// Behavior is the behavioral signal view (PLAN.md §3, §14).
type Behavior struct {
	// SameDaySamePairCount counts cases where the user opened more
	// than one trade on the same symbol on the same calendar day
	// (UTC). Strong proxy for revenge / over-commitment tendencies.
	SameDaySamePairCount int `json:"same_day_same_pair_count"`
	// AfterLossWithinHourCount counts cases where a trade opened
	// within 60 minutes of a losing close on the same user. Strong
	// proxy for revenge trading.
	AfterLossWithinHourCount int `json:"after_loss_within_hour_count"`
	// FridayCount / WeekdayCount: simple proxies for the PLAN.md
	// example "overtrading on Fridays".
	FridayTrades  int `json:"friday_trades"`
	WeekdayTrades int `json:"weekday_trades"`
	// MaxTradesInOneDay surfaces a possible overtrading day.
	MaxTradesInOneDay int `json:"max_trades_in_one_day"`
}

// TradeRow is the per-trade row we forward to the LLM. Only the
// fields the review actually needs are emitted to keep the payload
// bounded; this is the canonical contract with the engine.
type TradeRow struct {
	TradeID         string    `json:"trade_id"`
	Symbol          string    `json:"symbol"`
	Direction       string    `json:"direction"`
	TradingStyle    string    `json:"trading_style"`
	SetupType       string    `json:"setup_type"`
	Grade           string    `json:"grade"`
	Session         string    `json:"session"`
	ConfluenceScore float64   `json:"confluence_score"`
	RiskPercent     float64   `json:"risk_percent"`
	GrossPnL        float64   `json:"gross_pnl"`
	RMultiple       float64   `json:"r_multiple"`
	Outcome         string    `json:"outcome"`
	DurationMinutes int       `json:"duration_minutes"`
	SLAdjustments   int       `json:"sl_adjustments"`
	PartialCloses   int       `json:"partial_closes"`
	OpenedAt        time.Time `json:"opened_at"`
	ClosedAt        time.Time `json:"closed_at"`

	// Manual Journal subjective fields (only populated when
	// journal_mode = "manual"). Added directly to the TradeRow
	// because the Python LLM prompt passes this list exactly.
	RuleFollowed       string `json:"rule_followed,omitempty"`
	EmotionBeforeTrade string `json:"emotion_before_trade,omitempty"`
	EmotionAfterTrade  string `json:"emotion_after_trade,omitempty"`
	TradeQuality       string `json:"trade_quality,omitempty"`
	MistakeCategory    string `json:"mistake_category,omitempty"`
	NewsPresent        string `json:"news_present,omitempty"`
	Notes              string `json:"notes,omitempty"`
}

// Confidence is the deterministic data-quality stamp the LLM is
// required to honour (PLAN.md §11).
type Confidence struct {
	Band       string `json:"band"`
	SampleSize int    `json:"sample_size"`
	Note       string `json:"note"`
}

// Aggregate returns the full Bundle for the given user and inclusive
// window. Returns a Bundle with an empty Summary and Confidence.Band
// = "insufficient" when the user has no closed trades in the window.
func (a *PerformanceAggregator) Aggregate(
	ctx context.Context,
	userID string,
	period string,
	periodStart, periodEnd time.Time,
	journalMode string,
) (*Bundle, error) {
	if userID == "" {
		return nil, fmt.Errorf("performance_aggregator: user_id is required")
	}
	if periodEnd.Before(periodStart) {
		return nil, fmt.Errorf("performance_aggregator: period_end before period_start")
	}

	b := &Bundle{
		UserID:      userID,
		Period:      period,
		PeriodStart: periodStart,
		PeriodEnd:   periodEnd,
	}

	// Pull every closed trade in the window, ordered by closed_at
	// ASC so the streak + behavior detectors run in time order.
	rows, err := a.pool.Query(ctx, `
		SELECT trade_id, symbol, direction, trading_style, setup_type, grade, session,
		       confluence_score, risk_percent, gross_pnl, r_multiple, outcome,
		       duration_minutes, sl_adjustments, partial_closes,
		       opened_at, closed_at
		  FROM management_trades
		 WHERE status   = 'CLOSED'
		   AND user_id  = $1
		   AND closed_at >= $2
		   AND closed_at <= $3
		 ORDER BY closed_at ASC`,
		userID, periodStart, periodEnd,
	)
	if err != nil {
		return nil, fmt.Errorf("performance_aggregator: query trades: %w", err)
	}
	defer rows.Close()

	var all []TradeRow
	for rows.Next() {
		var (
			t        TradeRow
			closedAt *time.Time
		)
		if err := rows.Scan(
			&t.TradeID, &t.Symbol, &t.Direction, &t.TradingStyle, &t.SetupType, &t.Grade, &t.Session,
			&t.ConfluenceScore, &t.RiskPercent, &t.GrossPnL, &t.RMultiple, &t.Outcome,
			&t.DurationMinutes, &t.SLAdjustments, &t.PartialCloses,
			&t.OpenedAt, &closedAt,
		); err != nil {
			return nil, fmt.Errorf("performance_aggregator: scan: %w", err)
		}
		if closedAt != nil {
			t.ClosedAt = *closedAt
		}
		all = append(all, t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("performance_aggregator: rows: %w", err)
	}

	if journalMode == "manual" {
		if err := a.mergeManualJournal(ctx, userID, periodStart, periodEnd, &all); err != nil {
			a.log.Warn().Err(err).Str("user_id", userID).Msg("failed to merge manual journal; proceeding with system trades only")
		}
	}

	b.Confidence = computeConfidence(len(all))

	if len(all) == 0 {
		// Empty window. Initialise the maps so the JSON shape is
		// stable (the engine prompt explicitly checks for an empty
		// trades array and emits the canonical "not enough data"
		// review when the band is insufficient).
		b.BySession = []DimensionRow{}
		b.BySetup = []DimensionRow{}
		b.ByStyle = []DimensionRow{}
		b.ByGrade = []DimensionRow{}
		b.BySymbol = []DimensionRow{}
		b.ByDayOfWeek = []DimensionRow{}
		b.ByHourOfDay = []DimensionRow{}
		b.Trades = []TradeRow{}
		return b, nil
	}

	b.Summary = computeSummary(all)
	b.BySession = dimensionBreakdown(all, func(t TradeRow) string { return t.Session })
	b.BySetup = dimensionBreakdown(all, func(t TradeRow) string { return t.SetupType })
	b.ByStyle = dimensionBreakdown(all, func(t TradeRow) string { return t.TradingStyle })
	b.ByGrade = dimensionBreakdown(all, func(t TradeRow) string { return t.Grade })
	b.BySymbol = dimensionBreakdown(all, func(t TradeRow) string { return t.Symbol })
	b.ByDayOfWeek = dimensionBreakdown(all, func(t TradeRow) string {
		return t.OpenedAt.UTC().Weekday().String()
	})
	b.ByHourOfDay = dimensionBreakdown(all, func(t TradeRow) string {
		return fmt.Sprintf("%02d:00", t.OpenedAt.UTC().Hour())
	})
	b.Risk = computeRisk(all)
	b.Adherence = computeAdherence(all)
	b.Behavior = computeBehavior(all)

	// Slice trades for the LLM. We keep the most recent rows to bias
	// the narrative toward recency (PLAN.md is a *period* review and
	// the user cares more about the latest behavior than a 30-day-
	// old outlier).
	if len(all) <= MaxTradeRowsForLLM {
		b.Trades = all
	} else {
		b.Trades = all[len(all)-MaxTradeRowsForLLM:]
	}

	return b, nil
}

func computeSummary(trades []TradeRow) Summary {
	s := Summary{TotalTrades: len(trades)}
	if len(trades) == 0 {
		return s
	}
	var (
		sumR       float64
		bestR      = trades[0].RMultiple
		worstR     = trades[0].RMultiple
		sumDur     float64
		sumWinR    float64
		sumLossR   float64
		symbols    = make(map[string]struct{})
		setups     = make(map[string]struct{})
		currentW   int
		currentL   int
		durCount   int
	)
	for _, t := range trades {
		switch t.Outcome {
		case "WIN":
			s.Wins++
			sumWinR += t.RMultiple
			currentW++
			currentL = 0
			if currentW > s.MaxConsecutiveWins {
				s.MaxConsecutiveWins = currentW
			}
		case "LOSS":
			s.Losses++
			sumLossR += t.RMultiple
			currentL++
			currentW = 0
			if currentL > s.MaxConsecutiveLosses {
				s.MaxConsecutiveLosses = currentL
			}
		case "BREAKEVEN":
			s.Breakevens++
			currentW = 0
			currentL = 0
		}
		s.GrossPnL += t.GrossPnL
		sumR += t.RMultiple
		if t.RMultiple > bestR {
			bestR = t.RMultiple
		}
		if t.RMultiple < worstR {
			worstR = t.RMultiple
		}
		if t.DurationMinutes > 0 {
			sumDur += float64(t.DurationMinutes)
			durCount++
		}
		if t.Symbol != "" {
			symbols[t.Symbol] = struct{}{}
		}
		if t.SetupType != "" {
			setups[t.SetupType] = struct{}{}
		}
	}
	s.AvgRMultiple = roundTo(sumR/float64(len(trades)), 3)
	s.BestRMultiple = roundTo(bestR, 3)
	s.WorstRMultiple = roundTo(worstR, 3)
	s.WinRatePct = roundTo(float64(s.Wins)/float64(len(trades))*100, 2)
	s.LossRatePct = roundTo(float64(s.Losses)/float64(len(trades))*100, 2)
	if durCount > 0 {
		s.AvgDurationMinutes = roundTo(sumDur/float64(durCount), 2)
	}
	s.DistinctSymbols = len(symbols)
	s.DistinctSetups = len(setups)

	if s.Wins > 0 && s.Losses > 0 {
		avgWin := sumWinR / float64(s.Wins)
		avgLoss := math.Abs(sumLossR / float64(s.Losses))
		winRate := float64(s.Wins) / float64(len(trades))
		lossRate := float64(s.Losses) / float64(len(trades))
		s.Expectancy = roundTo((winRate*avgWin)-(lossRate*avgLoss), 3)
	}
	return s
}

func dimensionBreakdown(trades []TradeRow, key func(TradeRow) string) []DimensionRow {
	buckets := make(map[string]*DimensionRow)
	sums := make(map[string]float64)
	for _, t := range trades {
		k := key(t)
		if k == "" {
			k = "unspecified"
		}
		row, ok := buckets[k]
		if !ok {
			row = &DimensionRow{Key: k}
			buckets[k] = row
		}
		row.Trades++
		row.PnL += t.GrossPnL
		sums[k] += t.RMultiple
		switch t.Outcome {
		case "WIN":
			row.Wins++
		case "LOSS":
			row.Losses++
		}
	}
	out := make([]DimensionRow, 0, len(buckets))
	for k, row := range buckets {
		if row.Trades > 0 {
			row.WinRatePct = roundTo(float64(row.Wins)/float64(row.Trades)*100, 2)
			row.AvgR = roundTo(sums[k]/float64(row.Trades), 3)
			row.PnL = roundTo(row.PnL, 2)
		}
		out = append(out, *row)
	}
	// Stable ordering: descending by trade count, then by key.
	sort.Slice(out, func(i, j int) bool {
		if out[i].Trades != out[j].Trades {
			return out[i].Trades > out[j].Trades
		}
		return out[i].Key < out[j].Key
	})
	return out
}

func computeRisk(trades []TradeRow) Risk {
	r := Risk{}
	if len(trades) == 0 {
		return r
	}
	var sumRisk float64
	worstPnL := trades[0].GrossPnL
	for _, t := range trades {
		sumRisk += t.RiskPercent
		if t.RiskPercent > r.MaxRiskPercent {
			r.MaxRiskPercent = t.RiskPercent
		}
		if t.RiskPercent > 1.0 {
			r.TradesOverOnePct++
		}
		if t.RiskPercent > 1.5 {
			r.TradesOverOneHalfPct++
		}
		if t.RiskPercent > 2.0 {
			r.TradesOverTwoPct++
		}
		if t.GrossPnL < worstPnL {
			worstPnL = t.GrossPnL
		}
	}
	r.AvgRiskPercent = roundTo(sumRisk/float64(len(trades)), 3)
	r.MaxRiskPercent = roundTo(r.MaxRiskPercent, 3)
	r.WorstSingleTradePnL = roundTo(worstPnL, 2)
	return r
}

func computeAdherence(trades []TradeRow) Adherence {
	a := Adherence{}
	if len(trades) == 0 {
		return a
	}
	for _, t := range trades {
		a.TotalSLAdjustments += t.SLAdjustments
		a.TotalPartialCloses += t.PartialCloses
		if t.SLAdjustments > 0 {
			a.TradesWithSLMoved++
		}
		if t.PartialCloses > 0 {
			a.TradesWithPartials++
		}
	}
	a.AvgSLAdjustments = roundTo(float64(a.TotalSLAdjustments)/float64(len(trades)), 3)
	return a
}

func computeBehavior(trades []TradeRow) Behavior {
	b := Behavior{}
	if len(trades) == 0 {
		return b
	}

	// Friday counter.
	tradesByDay := make(map[string]int)
	for _, t := range trades {
		day := t.OpenedAt.UTC().Format("2006-01-02")
		tradesByDay[day]++
		if t.OpenedAt.UTC().Weekday() == time.Friday {
			b.FridayTrades++
		} else {
			b.WeekdayTrades++
		}
	}
	for _, count := range tradesByDay {
		if count > b.MaxTradesInOneDay {
			b.MaxTradesInOneDay = count
		}
	}

	// Same-day-same-pair: count pairs(day, symbol) with >1 trade.
	daySymbol := make(map[string]int)
	for _, t := range trades {
		key := t.OpenedAt.UTC().Format("2006-01-02") + "|" + t.Symbol
		daySymbol[key]++
	}
	for _, count := range daySymbol {
		if count > 1 {
			// Each extra trade beyond the first is the signal
			// (so a (day, symbol) with 3 trades contributes 2).
			b.SameDaySamePairCount += count - 1
		}
	}

	// After-loss-within-hour: for each trade, find the most recent
	// preceding close (any symbol) within 60 minutes. If it was a
	// LOSS, the current trade is a candidate.
	for i := 0; i < len(trades); i++ {
		cur := trades[i]
		for j := i - 1; j >= 0; j-- {
			prev := trades[j]
			if prev.ClosedAt.IsZero() {
				continue
			}
			delta := cur.OpenedAt.Sub(prev.ClosedAt)
			if delta < 0 || delta > time.Hour {
				break
			}
			if prev.Outcome == "LOSS" {
				b.AfterLossWithinHourCount++
				break
			}
		}
	}
	return b
}

func computeConfidence(sample int) Confidence {
	switch {
	case sample >= confHighMinTrades:
		return Confidence{
			Band:       "high",
			SampleSize: sample,
			Note:       fmt.Sprintf("High confidence based on %d closed trades.", sample),
		}
	case sample >= confMediumMinTrades:
		return Confidence{
			Band:       "medium",
			SampleSize: sample,
			Note:       fmt.Sprintf("Medium confidence based on %d closed trades; treat conclusions as directional.", sample),
		}
	case sample >= confLowMinTrades:
		return Confidence{
			Band:       "low",
			SampleSize: sample,
			Note:       fmt.Sprintf("Low confidence based on %d closed trades; avoid generalising from a small sample.", sample),
		}
	default:
		return Confidence{
			Band:       "insufficient",
			SampleSize: sample,
			Note:       "Insufficient closed trades in the window for a statistically meaningful review.",
		}
	}
}

func roundTo(v float64, places int) float64 {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return 0
	}
	shift := math.Pow(10, float64(places))
	return math.Round(v*shift) / shift
}

func (a *PerformanceAggregator) mergeManualJournal(
	ctx context.Context,
	userID string,
	periodStart, periodEnd time.Time,
	trades *[]TradeRow,
) error {
	var planRaw []byte
	err := a.pool.QueryRow(ctx, `
		SELECT plan
		  FROM user_trading_plans
		 WHERE user_id = $1
		   AND status  = 'active'
	`, userID).Scan(&planRaw)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil // No active plan, nothing to merge
		}
		return fmt.Errorf("query plan: %w", err)
	}

	type minimalPlan struct {
		Journal []struct {
			TradeID            string `json:"trade_id"`
			Date               string `json:"date"`
			RuleFollowed       string `json:"rule_followed"`
			EmotionBeforeTrade string `json:"emotion_before_trade"`
			EmotionAfterTrade  string `json:"emotion_after_trade"`
			TradeQuality       string `json:"trade_quality"`
			MistakeCategory    string `json:"mistake_category"`
			NewsPresent        string `json:"news_present"`
			Notes              string `json:"notes"`
			Session            string `json:"session"`
			Pair               string `json:"pair"`
			Direction          string `json:"direction"`
			Style              string `json:"style"`
			SetupType          string `json:"setup_type"`
			RiskPercent        string `json:"risk_percent"`
			RRPlanned          string `json:"rr_planned"`
			RRAchieved         string `json:"rr_achieved"`
			PnL                string `json:"pnl"`
			Outcome            string `json:"outcome"`
		} `json:"journal"`
	}

	var plan minimalPlan
	if err := json.Unmarshal(planRaw, &plan); err != nil {
		return fmt.Errorf("unmarshal plan: %w", err)
	}

	// 1. Index subjective data for autofilled trades
	subjectiveByTrade := make(map[string]int)
	for i, jrow := range plan.Journal {
		if jrow.TradeID != "" {
			subjectiveByTrade[jrow.TradeID] = i
		}
	}

	// 2. Merge subjective data into existing system trades
	for i := range *trades {
		t := &(*trades)[i]
		if idx, ok := subjectiveByTrade[t.TradeID]; ok {
			jrow := plan.Journal[idx]
			t.RuleFollowed = jrow.RuleFollowed
			t.EmotionBeforeTrade = jrow.EmotionBeforeTrade
			t.EmotionAfterTrade = jrow.EmotionAfterTrade
			t.TradeQuality = jrow.TradeQuality
			t.MistakeCategory = jrow.MistakeCategory
			t.NewsPresent = jrow.NewsPresent
			t.Notes = jrow.Notes
		}
	}

	// 3. Extract purely manual hand-typed trades
	for _, jrow := range plan.Journal {
		if jrow.TradeID != "" || jrow.Date == "" {
			continue
		}
		openedAt, err := parseDateRobustly(jrow.Date)
		if err != nil || openedAt.Before(periodStart) || openedAt.After(periodEnd) {
			continue
		}

		tr := TradeRow{
			Symbol:             jrow.Pair,
			Direction:          jrow.Direction,
			TradingStyle:       jrow.Style,
			SetupType:          jrow.SetupType,
			Session:            jrow.Session,
			Outcome:            strings.ToUpper(strings.TrimSpace(jrow.Outcome)),
			OpenedAt:           openedAt,
			ClosedAt:           openedAt,
			RiskPercent:        parseNumericString(jrow.RiskPercent),
			GrossPnL:           parseNumericString(jrow.PnL),
			RMultiple:          parseNumericString(jrow.RRAchieved),
			RuleFollowed:       jrow.RuleFollowed,
			EmotionBeforeTrade: jrow.EmotionBeforeTrade,
			EmotionAfterTrade:  jrow.EmotionAfterTrade,
			TradeQuality:       jrow.TradeQuality,
			MistakeCategory:    jrow.MistakeCategory,
			NewsPresent:        jrow.NewsPresent,
			Notes:              jrow.Notes,
		}

		*trades = append(*trades, tr)
	}

	// Re-sort by ClosedAt
	sort.Slice(*trades, func(i, j int) bool {
		return (*trades)[i].ClosedAt.Before((*trades)[j].ClosedAt)
	})

	return nil
}

func parseDateRobustly(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t, nil
	}
	if t, err := time.Parse("2006-01-02", s); err == nil {
		return t, nil
	}
	if t, err := time.Parse("02/01/2006", s); err == nil {
		return t, nil
	}
	if t, err := time.Parse("01/02/2006", s); err == nil {
		return t, nil
	}
	return time.Time{}, errors.New("unparseable date")
}

func parseNumericString(s string) float64 {
	s = strings.ReplaceAll(s, "$", "")
	s = strings.ReplaceAll(s, "R", "")
	s = strings.ReplaceAll(s, "%", "")
	s = strings.ReplaceAll(s, ",", "")
	s = strings.ReplaceAll(s, "+", "")
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	v, _ := strconv.ParseFloat(s, 64)
	return v
}

