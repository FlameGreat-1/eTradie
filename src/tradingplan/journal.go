package tradingplan

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/auth"
)

// ---------------------------------------------------------------------------
// Daily Execution Journal — composite view (manual-trade auto-populate)
//
// Design ref: docs/audit/TRADING_JOURNAL_AUTO_SYNC.md (§3 composite view,
// §5.3 gateway endpoints, §7 deterministic formatting, §8 edge cases).
//
// The journal section is a COMPOSITE: objective trade facts come live
// from the management service's manual-trade record (origin =
// MANUAL_RECONCILED) for the current 90-day window, joined by trade_id
// with the trader's saved subjective annotations (stored in the plan
// blob). Objective facts are NEVER copied into the plan; the journal is
// a one-way SINK (management -> view), never plan -> execution.
// ---------------------------------------------------------------------------

// ManualTradeFact is the gateway-internal, transport-agnostic projection
// of one manually-executed / reconciled trade returned by the management
// service. It mirrors managementv1.ManualJournalEntry field-for-field but
// is a plain struct so the tradingplan package never imports the
// generated proto types (the concrete reader in tradingplanadapter does
// the proto -> ManualTradeFact conversion). Same dependency-direction
// discipline as EngineDispatcher / BalanceProvider.
//
// Close cells (ExitPrice / RMultiple / GrossPnL / Outcome / ClosedAt)
// are zero / empty while IsOpen is true.
type ManualTradeFact struct {
	TradeID       string
	Symbol        string
	Direction     string // "BUY" | "SELL"
	TradingStyle  string
	SetupType     string
	EntryPrice    float64
	StopLoss      float64 // initial SL
	TP1Price      float64
	TP2Price      float64
	TP3Price      float64
	ExitPrice     float64 // 0 while open
	RiskPercent   float64
	TotalLotSize  float64
	RRRatio       float64 // planned R:R
	RMultiple     float64 // achieved R (0 while open)
	GrossPnL      float64 // realized P&L (0 while open)
	Outcome       string  // WIN | LOSS | BREAKEVEN | "" while open
	Session       string
	IsOpen        bool
	OpenedAt      string // RFC3339
	ClosedAt      string // RFC3339; "" while open
	BrokerOrderID string
}

// JournalReader is the narrow port the journal view needs from the
// management service. Declared here (not in infra) so the handler stays
// unit-testable with a fake and the tradingplan package never imports
// the gRPC client or the generated proto. The concrete implementation
// (management gRPC client wrapper) lives in tradingplanadapter and is
// injected via Handler.WithJournalReader.
//
// since / until bound the opened_at window (zero = unbounded on that
// side). limit / offset paginate the CLOSED set; open manual trades are
// always returned in full. The caller's identity is carried on ctx (the
// HTTP request context, which holds the raw JWT the management auth
// interceptor resolves the user from). totalClosed is the total closed
// manual trades in the window, for the UI's window-paging affordance.
type JournalReader interface {
	GetManualJournal(
		ctx context.Context,
		since, until time.Time,
		limit, offset int,
	) (facts []ManualTradeFact, totalClosed int, err error)
}

// WithJournalReader injects the management-backed manual-trade reader
// that powers the composite Daily Execution Journal. Optional, mirroring
// the other optional-dependency setters in the gateway (auth WithOAuth,
// metering WithSoftCapMailer): when it is nil the journal GET returns
// 503 so the gateway still boots cleanly when the management service is
// disabled or unreachable. Returns the receiver for chaining.
func (h *Handler) WithJournalReader(r JournalReader) *Handler {
	h.journalReader = r
	return h
}

// ---------------------------------------------------------------------------
// Window resolution
// ---------------------------------------------------------------------------

// journalWindowDays is the visible window the Daily Execution Journal
// shows by default (the 90-Day Trading Plan horizon). It is a DATE
// FILTER over the permanent management record, never a row cap: older
// manual trades stay in management_trades and are reached by paging the
// window back (window=previous). Nothing is ever trimmed.
const journalWindowDays = 90

// journalClosedPageSize is the default cap on CLOSED manual trades per
// window page when the client does not specify ?limit. It matches the
// management RPC default (200) and the plan annotation cap so the two
// stay in lockstep.
const journalClosedPageSize = 200

// resolveWindow maps the ?window= selector to an [since, until]
// opened_at range. "current" (the default, and any unrecognised value)
// is the most recent 90 days; "previous" is the 90 days before that, so
// the UI can page back through history without ever losing a trade.
func resolveWindow(window string, now time.Time) (since, until time.Time) {
	now = now.UTC()
	span := time.Duration(journalWindowDays) * 24 * time.Hour
	switch strings.ToLower(strings.TrimSpace(window)) {
	case "previous":
		until = now.Add(-span)
		since = until.Add(-span)
	default: // "current" or anything unrecognised
		until = now
		since = now.Add(-span)
	}
	return since, until
}

// ---------------------------------------------------------------------------
// Composite row shape (what the SPA renders)
// ---------------------------------------------------------------------------

// CompositeJournalRow is one Daily-Execution-Journal row as seen by the
// SPA: the OBJECTIVE cells (read-only, deterministically formatted from
// the management fact) plus the trader's SUBJECTIVE cells (from the
// saved annotation, editable). TradeID is the join key and the upsert
// key for the annotation PUT; IsOpen tells the UI to render the close
// cells as blank/"open" and disable export of an unfinished trade.
//
// All cells are strings so the SPA renders the formatted value verbatim
// (identical philosophy to JournalRow) and the Excel export is lossless.
type CompositeJournalRow struct {
	TradeID string `json:"trade_id"`
	IsOpen  bool   `json:"is_open"`

	// Objective (read-only, from management; formatted per §7).
	Date         string `json:"date"`
	Session      string `json:"session"`
	Pair         string `json:"pair"`
	Direction    string `json:"direction"`
	Style        string `json:"style"`
	SetupType    string `json:"setup_type"`
	Entry        string `json:"entry"`
	StopLoss     string `json:"stop_loss"`
	TakeProfit   string `json:"take_profit"`
	RiskPercent  string `json:"risk_percent"`
	PositionSize string `json:"position_size"`
	Exit         string `json:"exit"`
	RRPlanned    string `json:"rr_planned"`
	RRAchieved   string `json:"rr_achieved"`
	PnL          string `json:"pnl"`
	Outcome      string `json:"outcome"`

	// Subjective (editable, from the saved annotation).
	HTFBias            string `json:"htf_bias"`
	RuleFollowed       string `json:"rule_followed"`
	EmotionBeforeTrade string `json:"emotion_before_trade"`
	EmotionAfterTrade  string `json:"emotion_after_trade"`
	TradeQuality       string `json:"trade_quality"`
	MistakeCategory    string `json:"mistake_category"`
	NewsPresent        string `json:"news_present"`
	ScreenshotLink     string `json:"screenshot_link"`
	Notes              string `json:"notes"`
}

// ---------------------------------------------------------------------------
// GET /api/v1/trading-plan/journal
// ---------------------------------------------------------------------------

func (h *Handler) handleJournal(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.getJournal(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (h *Handler) getJournal(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if h.journalReader == nil {
		TradingPlanJournalTotal.WithLabelValues(outcomeError).Inc()
		writeError(w, http.StatusServiceUnavailable,
			"trade journal is temporarily unavailable")
		return
	}

	window := r.URL.Query().Get("window")
	loc := resolveLocation(r.URL.Query().Get("tz"))
	since, until := resolveWindow(window, time.Now())

	// Pull the OBJECTIVE facts (open + closed manual trades) for the
	// window from management. The request context carries the JWT the
	// management auth interceptor resolves the user from.
	facts, totalClosed, err := h.journalReader.GetManualJournal(
		r.Context(), since, until, journalClosedPageSize, 0,
	)
	if err != nil {
		TradingPlanJournalTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_journal_read_failed")
		writeError(w, http.StatusBadGateway, "failed to load trade journal")
		return
	}

	// Load the trader's saved SUBJECTIVE annotations from the plan blob
	// and index them by trade_id for the join. A missing plan is not an
	// error: the trader simply has no annotations yet, so every row
	// renders objective-only with blank subjective cells.
	annotations := map[string]JournalAnnotation{}
	if rec, perr := h.store.Get(r.Context(), userID); perr == nil && rec.Plan != nil {
		for _, a := range rec.Plan.JournalAnnotations {
			annotations[a.TradeID] = a
		}
	} else if perr != nil && !errors.Is(perr, ErrNotFound) {
		TradingPlanJournalTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(perr).Str("user_id", userID).Msg("trading_plan_journal_plan_read_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trade journal")
		return
	}

	rows := make([]CompositeJournalRow, 0, len(facts))
	for _, f := range facts {
		rows = append(rows, h.compositeRow(f, annotations[f.TradeID], loc))
	}

	TradingPlanJournalTotal.WithLabelValues(outcomeSuccess).Inc()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"window":       normalisedWindow(window),
		"rows":         rows,
		"total_closed": totalClosed,
		"window_days":  journalWindowDays,
	})
}

// compositeRow joins one objective management fact with the trader's
// saved subjective annotation into a fully-formatted SPA row. Objective
// close cells (exit / RR achieved / PnL / outcome) are left blank while
// the trade is open (§8.2).
func (h *Handler) compositeRow(f ManualTradeFact, a JournalAnnotation, loc *time.Location) CompositeJournalRow {
	row := CompositeJournalRow{
		TradeID: f.TradeID,
		IsOpen:  f.IsOpen,

		Date:         formatJournalDate(f.OpenedAt, loc),
		Session:      f.Session,
		Pair:         f.Symbol,
		Direction:    formatDirection(f.Direction),
		Style:        formatStyle(f.TradingStyle),
		SetupType:    f.SetupType,
		Entry:        formatPrice(f.EntryPrice),
		StopLoss:     formatPrice(f.StopLoss),
		TakeProfit:   formatTakeProfit(f.TP1Price, f.TP2Price, f.TP3Price),
		RiskPercent:  formatPercent(f.RiskPercent),
		PositionSize: formatLots(f.TotalLotSize),
		RRPlanned:    formatRR(f.RRRatio),

		HTFBias:            a.HTFBias,
		RuleFollowed:       a.RuleFollowed,
		EmotionBeforeTrade: a.EmotionBeforeTrade,
		EmotionAfterTrade:  a.EmotionAfterTrade,
		TradeQuality:       a.TradeQuality,
		MistakeCategory:    a.MistakeCategory,
		NewsPresent:        a.NewsPresent,
		ScreenshotLink:     a.ScreenshotLink,
		Notes:              a.Notes,
	}

	// Close cells fill only once management has closed the trade.
	if !f.IsOpen {
		row.Exit = formatPrice(f.ExitPrice)
		row.RRAchieved = formatRR(f.RMultiple)
		row.PnL = formatPnL(f.GrossPnL, h.planCurrency)
		row.Outcome = f.Outcome
	}
	return row
}

// ---------------------------------------------------------------------------
// PUT /api/v1/trading-plan/journal/annotation
// ---------------------------------------------------------------------------

func (h *Handler) handleJournalAnnotation(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	h.putJournalAnnotation(w, r)
}

func (h *Handler) putJournalAnnotation(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	// Rate-limited like the in-app edit path (design §5.3).
	if !h.editLimiter.Allow(userID) {
		TradingPlanRateLimitedTotal.WithLabelValues(endpointJournalAnnotation).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many edit requests; try again shortly")
		return
	}

	// 16 KB is generous: one annotation is the trader's nine subjective
	// free-text cells (each capped at 120 chars by Validate).
	r.Body = http.MaxBytesReader(w, r.Body, 16*1024)
	var in JournalAnnotation
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	in.TradeID = strings.TrimSpace(in.TradeID)
	if in.TradeID == "" {
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "trade_id is required")
		return
	}

	// Load the current plan; the annotation can only attach to an
	// existing plan (the journal lives inside it). 404 mirrors the
	// edit path's "generate one first" contract.
	rec, err := h.store.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, ErrNotFound) || rec == nil || rec.Plan == nil {
			TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
			writeError(w, http.StatusNotFound, "no trading plan to annotate; generate one first")
			return
		}
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_annotation_plan_read_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading plan")
		return
	}
	if rec.Plan == nil {
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusNotFound, "no trading plan to annotate; generate one first")
		return
	}

	// Upsert by trade_id: replace an existing annotation in place,
	// otherwise append. Validate (called via UpdatePlanContent's path)
	// also de-dupes defensively, but doing it here keeps the stored
	// order stable (existing rows keep their position).
	plan := rec.Plan
	replaced := false
	for i := range plan.JournalAnnotations {
		if plan.JournalAnnotations[i].TradeID == in.TradeID {
			plan.JournalAnnotations[i] = in
			replaced = true
			break
		}
	}
	if !replaced {
		plan.JournalAnnotations = append(plan.JournalAnnotations, in)
	}

	// Validate normalises + trims + caps the whole plan (including the
	// annotation list) before persistence, exactly like the edit path.
	if err := Validate(plan); err != nil {
		var verr *ValidationError
		if errors.As(err, &verr) {
			TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
			writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
				"error":  verr.Message,
				"fields": verr.Fields,
			})
			return
		}
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	if _, err := h.store.UpdatePlanContent(r.Context(), userID, plan); err != nil {
		if errors.Is(err, ErrNotFound) {
			TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeValidationError).Inc()
			writeError(w, http.StatusNotFound, "no trading plan to annotate; generate one first")
			return
		}
		TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_annotation_save_failed")
		writeError(w, http.StatusInternalServerError, "failed to save annotation")
		return
	}

	TradingPlanJournalAnnotationTotal.WithLabelValues(outcomeSuccess).Inc()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"saved":    true,
		"trade_id": in.TradeID,
	})
}

// ---------------------------------------------------------------------------
// Deterministic formatting (design §7). One helper per cell type so the
// objective cells render identically across the SPA table, the Excel
// export, and any future surface.
// ---------------------------------------------------------------------------

// resolveLocation maps an optional IANA tz query param to a *Location,
// falling back to UTC when empty or invalid. Mirrors the pnl-calendar
// tz convention: the visible Date/Session cell is rendered in the
// trader's timezone, never raw UTC.
func resolveLocation(tz string) *time.Location {
	tz = strings.TrimSpace(tz)
	if tz == "" {
		return time.UTC
	}
	if loc, err := time.LoadLocation(tz); err == nil {
		return loc
	}
	return time.UTC
}

// normalisedWindow echoes the resolved window selector back to the SPA
// so the UI can label the visible page and drive the prev/next control.
func normalisedWindow(window string) string {
	if strings.EqualFold(strings.TrimSpace(window), "previous") {
		return "previous"
	}
	return "current"
}

// formatJournalDate renders an RFC3339 opened_at timestamp as a
// date-time in the trader's timezone (YYYY-MM-DD HH:MM). An empty or
// unparseable input yields an empty cell rather than a misleading zero
// time.
func formatJournalDate(rfc3339 string, loc *time.Location) string {
	rfc3339 = strings.TrimSpace(rfc3339)
	if rfc3339 == "" {
		return ""
	}
	t, err := time.Parse(time.RFC3339, rfc3339)
	if err != nil {
		return ""
	}
	return t.In(loc).Format("2006-01-02 15:04")
}

// formatDirection maps the broker BUY/SELL convention to the trader-
// facing Long/Short label used throughout the workbook. Unknown values
// pass through trimmed so nothing is silently dropped.
func formatDirection(dir string) string {
	switch strings.ToUpper(strings.TrimSpace(dir)) {
	case "BUY":
		return "Long"
	case "SELL":
		return "Short"
	default:
		return strings.TrimSpace(dir)
	}
}

// formatStyle title-cases the management trading-style enum
// ("INTRADAY" -> "Intraday") for display. Unknown values pass through.
func formatStyle(style string) string {
	style = strings.TrimSpace(style)
	if style == "" {
		return ""
	}
	lower := strings.ToLower(style)
	return strings.ToUpper(lower[:1]) + lower[1:]
}

// formatPrice renders an instrument price by trimming trailing zeros
// (instrument digits are not carried on ManualJournalEntry, so we use a
// generous fixed precision and trim, which is correct for both 5-digit
// FX and 2-digit indices). A zero price yields an empty cell (e.g. an
// unset TP or an open trade's exit).
func formatPrice(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	s := strconv.FormatFloat(v, 'f', 8, 64)
	if strings.Contains(s, ".") {
		s = strings.TrimRight(s, "0")
		s = strings.TrimRight(s, ".")
	}
	return s
}

// formatTakeProfit joins the up-to-three TP legs into one cell
// ("1.2345 / 1.2400 / 1.2500"), skipping unset (zero) legs. Mirrors how
// a manual journal records a multi-target plan in a single column.
func formatTakeProfit(tp1, tp2, tp3 float64) string {
	parts := make([]string, 0, 3)
	for _, tp := range []float64{tp1, tp2, tp3} {
		if s := formatPrice(tp); s != "" {
			parts = append(parts, s)
		}
	}
	return strings.Join(parts, " / ")
}

// formatPercent renders a risk percent as stored ("1%", "0.5%"). A zero
// risk yields an empty cell.
func formatPercent(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	s := strconv.FormatFloat(v, 'f', -1, 64)
	return s + "%"
}

// formatLots renders a position size in lots at 2 dp (the broker min
// lot step is 0.01). A zero size yields an empty cell.
func formatLots(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}

// formatRR renders a risk:reward / R-multiple at 2 dp. A zero value
// yields an empty cell (e.g. R-achieved while the trade is still open).
func formatRR(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}

// formatPnL renders realized P&L at 2 dp suffixed with the plan/account
// currency ("125.40 USD"). When the currency is unknown the bare number
// is returned. Negative values keep their sign.
func formatPnL(v float64, currency string) string {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	n := strconv.FormatFloat(v, 'f', 2, 64)
	currency = strings.TrimSpace(currency)
	if currency == "" {
		return n
	}
	return fmt.Sprintf("%s %s", n, currency)
}
