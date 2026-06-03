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
	ManualTrades(ctx context.Context) ([]ManualTradeFact, error)
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

// mergeManualTrades fills the OBJECTIVE cells of the plan's existing
// journal rows from the user's manual trades, in place. Returns true
// when the plan was modified (so the caller persists it).
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
//   3. Otherwise append a new row (respecting journalMaxRows).
//
// The trader's SUBJECTIVE cells are never written; rows bound to other
// trades and hand-typed rows (no TradeID, but non-empty) are skipped
// when scanning for a blank slot, so nothing the trader did is ever
// clobbered.
func mergeManualTrades(p *Plan, facts []ManualTradeFact, loc *time.Location) bool {
	if p == nil || len(facts) == 0 {
		return false
	}
	if loc == nil {
		loc = time.UTC
	}

	// Index existing rows already bound to a trade.
	boundRow := make(map[string]int, len(p.Journal))
	for i := range p.Journal {
		if id := p.Journal[i].TradeID; id != "" {
			boundRow[id] = i
		}
	}

	changed := false
	for _, f := range facts {
		if f.TradeID == "" {
			continue
		}
		if idx, ok := boundRow[f.TradeID]; ok {
			// Update the already-bound row in place.
			if applyObjectiveCells(&p.Journal[idx], f, loc) {
				changed = true
			}
			continue
		}
		// Claim the next fully-blank seed row.
		if idx := nextBlankRow(p.Journal); idx >= 0 {
			p.Journal[idx].TradeID = f.TradeID
			applyObjectiveCells(&p.Journal[idx], f, loc)
			boundRow[f.TradeID] = idx
			changed = true
			continue
		}
		// No blank row left: append (respect the cap).
		if len(p.Journal) >= journalMaxRows {
			continue
		}
		row := JournalRow{TradeID: f.TradeID}
		applyObjectiveCells(&row, f, loc)
		p.Journal = append(p.Journal, row)
		boundRow[f.TradeID] = len(p.Journal) - 1
		changed = true
	}
	return changed
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