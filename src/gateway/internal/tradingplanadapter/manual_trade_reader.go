package tradingplanadapter

import (
	"context"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
	"github.com/flamegreat-1/etradie/src/tradingplan"
)

// ManualTradeReader is the concrete tradingplan.ManualTradeReader. It
// adapts the gateway's management gRPC client to the narrow port the
// Daily Execution Journal auto-populate needs, converting the generated
// proto ManualJournalEntry messages into transport-agnostic
// tradingplan.ManualTradeFact values.
//
// The package exists so the tradingplan package never imports the
// generated proto types or the gRPC client (mirrors the Dispatcher /
// Balance adapters): the dependency graph stays one-directional
//
//	tradingplan          -> (interface declarations)
//	tradingplanadapter   -> tradingplan + management + proto (concrete)
//	container            -> both (composition)
type ManualTradeReader struct {
	client *management.Client
}

// manualJournalClosedFetchLimit bounds the CLOSED manual-trade set the
// reader pulls per plan load. It is deliberately well above the trading
// plan's journal cap (tradingplan.journalMaxRows = 200 rows total,
// covering both auto-filled and hand-typed rows): since the auto-fill
// can bind at most that many manual trades into the journal, fetching
// the newest 500 closed trades guarantees every closed trade that could
// possibly occupy a journal row is present in a single read. The repo
// returns them newest-first (ORDER BY closed_at DESC), so for a trader
// with a very large history it is the most recent closed trades that
// are kept — exactly the ones the 90-day journal is about. No
// pagination is needed because anything beyond the cap can never be
// bound to a row.
const manualJournalClosedFetchLimit = 500

// NewManualTradeReader builds a ManualTradeReader. When the management
// client is nil (management disabled or unreachable at startup), it
// returns nil so the caller can inject a nil tradingplan.ManualTradeReader
// and let the handler simply skip auto-fill instead of panicking on a
// nil client.
func NewManualTradeReader(client *management.Client) *ManualTradeReader {
	if client == nil {
		return nil
	}
	return &ManualTradeReader{client: client}
}

// ManualTrades satisfies tradingplan.ManualTradeReader. It fetches the
// authenticated user's manually-executed / reconciled trades (open +
// closed; the management handler already filters to
// origin=MANUAL_RECONCILED and excludes SYSTEM + MANUAL_RESTORED).
//
// The window is unbounded (empty since/until) because the journal
// auto-fill binds every manual trade to a row in place; it is not a
// date-paged view. The closed set is bounded by
// manualJournalClosedFetchLimit (see its doc): the plan journal can
// hold at most ~200 rows total, so fetching the newest 500 closed
// trades guarantees every trade that could possibly land in the journal
// is present in one read, and pagination is unnecessary. Open trades
// are always returned in full by the server. The caller's JWT travels
// on ctx and is forwarded by the client so the management auth
// interceptor resolves the same user.
func (m *ManualTradeReader) ManualTrades(ctx context.Context) ([]tradingplan.ManualTradeFact, error) {
	req := &managementv1.GetManualJournalRequest{
		Limit: manualJournalClosedFetchLimit,
	}
	resp, err := m.client.GetManualJournal(ctx, req)
	if err != nil {
		return nil, err
	}
	if resp == nil {
		return nil, nil
	}

	entries := resp.GetEntries()
	facts := make([]tradingplan.ManualTradeFact, 0, len(entries))
	for _, e := range entries {
		if e == nil {
			continue
		}
		facts = append(facts, tradingplan.ManualTradeFact{
			TradeID:      e.GetTradeId(),
			Symbol:       e.GetSymbol(),
			Direction:    e.GetDirection(),
			TradingStyle: e.GetTradingStyle(),
			SetupType:    e.GetSetupType(),
			EntryPrice:   e.GetEntryPrice(),
			StopLoss:     e.GetStopLoss(),
			TP1Price:     e.GetTp1Price(),
			TP2Price:     e.GetTp2Price(),
			TP3Price:     e.GetTp3Price(),
			ExitPrice:    e.GetExitPrice(),
			RiskPercent:  e.GetRiskPercent(),
			TotalLotSize: e.GetTotalLotSize(),
			RRRatio:      e.GetRrRatio(),
			RMultiple:    e.GetRMultiple(),
			GrossPnL:     e.GetGrossPnl(),
			Outcome:      e.GetOutcome(),
			Session:      e.GetSession(),
			IsOpen:       e.GetIsOpen(),
			OpenedAt:     e.GetOpenedAt(),
			ClosedAt:     e.GetClosedAt(),
		})
	}
	return facts, nil
}
