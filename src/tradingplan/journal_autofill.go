package tradingplan

import (
	"context"
	"math"
	"strconv"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// Daily Execution Journal auto-populate (manual trades).
//
// The Daily Execution Journal (Section 3) is the trader's MANUAL-trading
// workbook. The moment the trader executes a manual trade and the system
// reconciles it, the OBJECTIVE cells of a journal row are filled for
// them (pair, direction, entry, SL, TP, size, and — as the trade
// progresses — exit, P&L, R:R, outcome). The trader then only fills the
// SUBJECTIVE cells (emotions, quality, mistake, rule-followed, HTF bias,
// screenshot, notes).
//
// We do NOT add a separate table, columns, rows, endpoints or model:
// we fill the EXISTING JournalRow rows in place. One trade = one row,
// bound by the hidden JournalRow.TradeID, filled into the next blank
// seed row and updated in place as the trade progresses.
//
// Scope (authoritative, from the management `origin` discriminator):
//   - ONLY manually-executed / reconciled trades (origin =
//     MANUAL_RECONCILED) populate the journal.
//   - System-executed trades are shown elsewhere in the dashboard and
//     are EXCLUDED.
//   - MANUAL_RESTORED history-import rows (zeroed entry/SL/TP) are
//     EXCLUDED.
// The management read path already enforces this; the gateway just
// consumes what it returns.
// ---------------------------------------------------------------------------

// ManualTradeFact is the gateway-internal, transport-agnostic projection
// of one manually-executed / reconciled trade. It mirrors the objective
// facts the management service exposes; it is a plain struct so the
// tradingplan package never imports the generated proto types (the
// concrete reader in tradingplanadapter does the proto -> fact
// conversion). Same dependency discipline as EngineDispatcher /
// BalanceProvider.
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
}

// ManualTradeReader is the narrow port the auto-populate needs from the
// management service: the user's manually-executed / reconciled trades
// (open + closed), already filtered to origin=MANUAL_RECONCILED.
// Declared here (not in infra) so the handler stays unit-testable with a
// fake and the tradingplan package never imports the gRPC client or the
// generated proto. The concrete implementation lives in
// tradingplanadapter and is injected via Handler.WithManualTradeReader.
//
// The caller's identity is carried on ctx (the HTTP request context,
// which holds the raw JWT the management auth interceptor resolves the
// user from).
type ManualTradeReader interface {
	// ManualTrades returns all of the user's manual trades (open +
	// closed) for the auto-fill of the CURRENT window. Unbounded read.
	ManualTrades(ctx context.Context) ([]ManualTradeFact, error)

	// ManualTradesWindow returns the user's manual trades whose open
	// date falls in [since, until], paginated by limit/offset, plus the
	// total closed count in that window (for the UI pager). It powers
	// the read-only journal history view that pages back through
	// PREVIOUS 90-day windows; those trades are served from the
	// permanent management_trades record, never written to the plan.
	ManualTradesWindow(
		ctx context.Context,
		since, until time.Time,
		limit, offset int,
	) (facts []ManualTradeFact, totalClosed int, err error)
}

// WithManualTradeReader injects the management-backed reader that feeds
// the journal auto-populate. Optional, mirroring the other
// optional-dependency setters in the gateway: when it is nil the
// journal simply is not auto-filled (the plan loads normally and the
// trader fills rows by hand). Returns the receiver for chaining.
func (h *Handler) WithManualTradeReader(r ManualTradeReader) *Handler {
	h.manualTrades = r
	return h
}

// journalWindowDays is the rolling window the auto-fill keeps in the
// plan blob. The Daily Execution Journal is a 90-day workbook: only
// manual trades opened within the last journalWindowDays populate the
// plan. Older trades are never lost — their objective facts live
// permanently in management_trades and the UI pages back to previous
// windows. The window (not a fixed row count) is what bounds the blob,
// so the journal keeps logging forever.
const journalWindowDays = 90

// mergeStats reports the outcome of a mergeManualTrades pass so the
// caller can decide whether to persist and can emit metrics.
type mergeStats struct {
	Updated  int // existing bound rows whose objective cells changed
	Filled   int // blank seed rows newly claimed + bound
	Appended int // new rows appended past the seeded blanks
	Rolled   int // auto rows reclaimed because they fell out of the window
	Capped   int // trades not placed because journalMaxRows is full (extreme)
}

// changed reports whether the merge actually mutated the plan blob (so
// the caller persists). A capped-only pass changes nothing and must NOT
// trigger a write; a roll-out DOES change the blob.
func (m mergeStats) changed() bool {
	return m.Updated > 0 || m.Filled > 0 || m.Appended > 0 || m.Rolled > 0
}

// mergeManualTrades fills the OBJECTIVE cells of the plan's existing
// journal rows from the user's manual trades, in place. Returns a
// mergeStats describing what happened (so the caller can persist +
// emit metrics, and so the cap-hit drop is observable).
//
// loc renders the Date cell in the trader's timezone (forwarded as ?tz
// on the plan GET); a nil loc is treated as UTC so the result stays
// deterministic when no tz is supplied.
//
// Binding rule (one trade = one row):
//   1. If a row already carries this trade's TradeID, update its
//      objective cells in place (handles open -> close progression).
//   2. Otherwise claim the NEXT fully-blank seed row (no TradeID and
//      every cell empty), bind it, and fill the objective cells.
//   3. Otherwise append a new row (respecting journalMaxRows); when the
//      cap is reached the trade is counted as Capped (surfaced by the
//      caller) rather than silently dropped.
//
// The trader's SUBJECTIVE cells are never written; rows bound to other
// trades and hand-typed rows (no TradeID, but non-empty) are skipped
// when scanning for a blank slot, so nothing the trader did is ever
// clobbered.
//
// Windowing (W1): only facts opened within the last journalWindowDays
// are merged; auto-bound rows whose trade fell out of the window are
// rolled out (reset to blank) UNLESS the trader annotated them, so the
// blob holds the current window plus any annotated rows and the
// journal keeps logging forever without a fixed row cap. now is the
// window anchor (caller passes time.Now()).
func mergeManualTrades(p *Plan, facts []ManualTradeFact, loc *time.Location, now time.Time) mergeStats {
	var stats mergeStats
	if p == nil {
		return stats
	}
	if loc == nil {
		loc = time.UTC
	}

	// Set of trades that are in the current window (by open date). Used
	// both to gate merging and to decide which bound rows to roll out.
	inWindow := make(map[string]bool, len(facts))
	for _, f := range facts {
		if f.TradeID != "" && factInWindow(f, now) {
			inWindow[f.TradeID] = true
		}
	}

	// ROLL-OUT phase: reclaim auto-bound rows whose trade is no longer
	// in the window, so the seed slots free up and the blob tracks the
	// current 90-day window. An annotated row (the trader typed a
	// subjective cell) is ALWAYS kept — never lose human work.
	for i := range p.Journal {
		id := p.Journal[i].TradeID
		if id == "" {
			continue // hand-typed or blank row: never touched here.
		}
		if inWindow[id] {
			continue // still in the current window.
		}
		if rowHasAnnotation(&p.Journal[i]) {
			continue // trader annotated it: keep regardless of window.
		}
		// Stale, unannotated auto row -> reset to a blank, unbound slot.
		// Its objective facts remain in management_trades.
		p.Journal[i] = JournalRow{}
		stats.Rolled++
	}

	// Index existing rows already bound to a trade (post roll-out).
	boundRow := make(map[string]int, len(p.Journal))
	for i := range p.Journal {
		if id := p.Journal[i].TradeID; id != "" {
			boundRow[id] = i
		}
	}

	for _, f := range facts {
		if f.TradeID == "" {
			continue
		}
		if idx, ok := boundRow[f.TradeID]; ok {
			// Update the already-bound row in place (open -> close), even
			// if it is now just outside the window: a row already in the
			// blob is kept current until it rolls out on a later pass.
			if applyObjectiveCells(&p.Journal[idx], f, loc) {
				stats.Updated++
			}
			continue
		}
		// New trade: only place it when it is in the current window.
		// Out-of-window trades belong to a previous window the UI pages
		// to (read from management_trades), not the live blob.
		if !factInWindow(f, now) {
			continue
		}
		// Claim the next fully-blank seed row.
		if idx := nextBlankRow(p.Journal); idx >= 0 {
			p.Journal[idx].TradeID = f.TradeID
			applyObjectiveCells(&p.Journal[idx], f, loc)
			boundRow[f.TradeID] = idx
			stats.Filled++
			continue
		}
		// No blank row left: append, unless the final hard safety bound
		// is reached. After roll-out this is only possible with >200
		// annotated rows inside one window; surface it (metric + log)
		// rather than lose the trade silently.
		if len(p.Journal) >= journalMaxRows {
			stats.Capped++
			continue
		}
		row := JournalRow{TradeID: f.TradeID}
		applyObjectiveCells(&row, f, loc)
		p.Journal = append(p.Journal, row)
		boundRow[f.TradeID] = len(p.Journal) - 1
		stats.Appended++
	}

	// Compact fully-blank unbound rows so they don't linger in the UI
	// or Excel export.
	compacted := make([]JournalRow, 0, len(p.Journal))
	for i := range p.Journal {
		if p.Journal[i].TradeID == "" && rowIsEmpty(&p.Journal[i]) {
			continue
		}
		compacted = append(compacted, p.Journal[i])
	}
	p.Journal = compacted

	return stats
}

// journalHistoryPageSize is the page size for the read-only journal
// history endpoint (previous-window page-back). Fixed server-side so a
// client cannot request an unbounded page.
const journalHistoryPageSize = 50

// rowFromFact renders a manual-trade fact into a read-only JournalRow
// using the SAME deterministic formatters as the live auto-fill, so a
// history row is identical to a live journal row. Used only by the
// read-only history endpoint; it never touches the plan blob. The
// subjective cells are left blank (previous-window history shows the
// objective record; annotations live in the current plan blob).
func rowFromFact(f ManualTradeFact, loc *time.Location) JournalRow {
	var row JournalRow
	row.TradeID = f.TradeID
	applyObjectiveCells(&row, f, loc)
	return row
}

// journalWindowBounds returns the [since, until] open-date range for the
// Nth journal window ending at now: window 0 is the current
// [now-journalWindowDays, now]; window 1 is the previous
// [now-2*window, now-1*window]; and so on. A negative window is clamped
// to 0.
func journalWindowBounds(window int, now time.Time) (since, until time.Time) {
	if window < 0 {
		window = 0
	}
	span := time.Duration(journalWindowDays) * 24 * time.Hour
	until = now.Add(-time.Duration(window) * span)
	since = until.Add(-span)
	return since, until
}

// factInWindow reports whether a manual trade's open date is within the
// current journalWindowDays window ending at now. An empty or
// unparseable OpenedAt is treated as in-window so a bad timestamp never
// silently drops a trade from the live journal.
func factInWindow(f ManualTradeFact, now time.Time) bool {
	ts := strings.TrimSpace(f.OpenedAt)
	if ts == "" {
		return true
	}
	opened, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		return true
	}
	cutoff := now.Add(-time.Duration(journalWindowDays) * 24 * time.Hour)
	return !opened.Before(cutoff)
}

// rowHasAnnotation reports whether the trader has filled ANY subjective
// cell on the row. Such a row is never rolled out by the window, so no
// human work is ever lost. The objective cells are excluded because
// they are system-owned (auto-filled).
func rowHasAnnotation(r *JournalRow) bool {
	return r.HTFBias != "" || r.RuleFollowed != "" || r.EmotionBeforeTrade != "" ||
		r.EmotionAfterTrade != "" || r.TradeQuality != "" || r.MistakeCategory != "" ||
		r.NewsPresent != "" || r.ScreenshotLink != "" || r.Notes != ""
}

// nextBlankRow returns the index of the first fully-blank, unbound row
// (no TradeID and every cell empty), or -1 when none remains. A row the
// trader has started typing into (any cell non-empty) is theirs and is
// skipped, so the auto-fill never overwrites manual work.
func nextBlankRow(rows []JournalRow) int {
	for i := range rows {
		if rows[i].TradeID == "" && rowIsEmpty(&rows[i]) {
			return i
		}
	}
	return -1
}

// rowIsEmpty reports whether every visible cell of the row is blank.
func rowIsEmpty(r *JournalRow) bool {
	return r.Date == "" && r.Session == "" && r.Pair == "" && r.Direction == "" &&
		r.Style == "" && r.SetupType == "" && r.HTFBias == "" && r.Entry == "" &&
		r.StopLoss == "" && r.TakeProfit == "" && r.RiskPercent == "" &&
		r.PositionSize == "" && r.Exit == "" && r.RRPlanned == "" &&
		r.RRAchieved == "" && r.PnL == "" && r.Outcome == "" &&
		r.RuleFollowed == "" && r.EmotionBeforeTrade == "" &&
		r.EmotionAfterTrade == "" && r.TradeQuality == "" &&
		r.MistakeCategory == "" && r.NewsPresent == "" &&
		r.ScreenshotLink == "" && r.Notes == ""
}

// applyObjectiveCells writes the objective facts onto a row, leaving the
// trader's subjective cells (HTFBias, RuleFollowed, emotions,
// TradeQuality, MistakeCategory, NewsPresent, ScreenshotLink, Notes)
// untouched. Returns true if any objective cell changed.
//
// Close cells (Exit / RRAchieved / PnL / Outcome) stay blank while the
// trade is open and fill once management closes it.
func applyObjectiveCells(r *JournalRow, f ManualTradeFact, loc *time.Location) bool {
	before := *r

	r.Date = formatJournalDate(f.OpenedAt, loc)
	r.Session = f.Session
	r.Pair = f.Symbol
	r.Direction = formatDirection(f.Direction)
	r.Style = formatStyle(f.TradingStyle)
	r.SetupType = f.SetupType
	r.Entry = formatPrice(f.EntryPrice)
	r.StopLoss = formatPrice(f.StopLoss)
	r.TakeProfit = formatTakeProfit(f.TP1Price, f.TP2Price, f.TP3Price)
	r.RiskPercent = formatPercent(f.RiskPercent)
	r.PositionSize = formatLots(f.TotalLotSize)
	r.RRPlanned = formatRR(f.RRRatio)

	if f.IsOpen {
		r.Exit = ""
		r.RRAchieved = ""
		r.PnL = ""
		r.Outcome = ""
	} else {
		r.Exit = formatPrice(f.ExitPrice)
		r.RRAchieved = formatRR(f.RMultiple)
		r.PnL = formatPnL(f.GrossPnL)
		r.Outcome = f.Outcome
	}

	return *r != before
}

// ---------------------------------------------------------------------------
// Deterministic cell formatting. The journal is all-strings; these write
// the objective values the trader sees verbatim.
// ---------------------------------------------------------------------------

// formatJournalDate renders an RFC3339 opened_at as "YYYY-MM-DD HH:MM"
// in the supplied timezone (nil -> UTC). Empty / unparseable -> empty
// cell.
func formatJournalDate(rfc3339 string, loc *time.Location) string {
	rfc3339 = strings.TrimSpace(rfc3339)
	if rfc3339 == "" {
		return ""
	}
	t, err := time.Parse(time.RFC3339, rfc3339)
	if err != nil {
		return ""
	}
	if loc == nil {
		loc = time.UTC
	}
	return t.In(loc).Format("2006-01-02 15:04")
}

// formatDirection maps the broker BUY/SELL convention to the trader-
// facing Long/Short label. Unknown values pass through trimmed.
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
// ("INTRADAY" -> "Intraday"). Unknown values pass through.
func formatStyle(style string) string {
	style = strings.TrimSpace(style)
	if style == "" {
		return ""
	}
	lower := strings.ToLower(style)
	return strings.ToUpper(lower[:1]) + lower[1:]
}

// formatPrice renders an instrument price by trimming trailing zeros
// (instrument digits are not carried on the fact, so a generous fixed
// precision + trim is correct for both 5-digit FX and 2-digit indices).
// Zero -> empty cell (e.g. an unset TP or an open trade's exit).
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

// formatTakeProfit joins the up-to-three TP legs into one cell,
// skipping unset (zero) legs.
func formatTakeProfit(tp1, tp2, tp3 float64) string {
	parts := make([]string, 0, 3)
	for _, tp := range []float64{tp1, tp2, tp3} {
		if s := formatPrice(tp); s != "" {
			parts = append(parts, s)
		}
	}
	return strings.Join(parts, " / ")
}

// formatPercent renders a risk percent as stored ("1%"). Zero -> empty.
func formatPercent(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', -1, 64) + "%"
}

// formatLots renders a position size in lots at 2 dp. Zero -> empty.
func formatLots(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}

// formatRR renders an R:R / R-multiple at 2 dp. Zero -> empty (e.g.
// R-achieved while the trade is still open).
func formatRR(v float64) string {
	if v == 0 || math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}

// formatPnL renders realized P&L at 2 dp. Negative values keep sign.
func formatPnL(v float64) string {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return ""
	}
	return strconv.FormatFloat(v, 'f', 2, 64)
}