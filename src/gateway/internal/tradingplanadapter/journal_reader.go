package tradingplanadapter

import (
	"context"
	"time"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
	"github.com/flamegreat-1/etradie/src/tradingplan"
)

// JournalReader is the concrete tradingplan.JournalReader. It adapts the
// gateway's management gRPC client to the narrow port the trading-plan
// Daily Execution Journal composite view needs, converting the generated
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
type JournalReader struct {
	client *management.Client
}

// NewJournalReader builds a JournalReader. When the management client is
// nil (management disabled or unreachable at startup), it returns nil so
// the caller can inject a nil tradingplan.JournalReader and let the
// handler degrade the journal GET to a clean 503 instead of panicking on
// a nil client.
func NewJournalReader(client *management.Client) *JournalReader {
	if client == nil {
		return nil
	}
	return &JournalReader{client: client}
}

// GetManualJournal satisfies tradingplan.JournalReader.
//
// since / until are the opened_at window bounds; a zero time means
// unbounded on that side and is sent as an empty RFC3339 string (the
// management handler treats "" as unbounded). limit / offset paginate
// the CLOSED set; open manual trades are always returned in full by the
// server. The caller's JWT travels on ctx and is forwarded by the
// client so the management auth interceptor resolves the same user.
func (j *JournalReader) GetManualJournal(
	ctx context.Context,
	since, until time.Time,
	limit, offset int,
) ([]tradingplan.ManualTradeFact, int, error) {
	req := &managementv1.GetManualJournalRequest{
		SinceRfc3339: rfc3339OrEmpty(since),
		UntilRfc3339: rfc3339OrEmpty(until),
		Limit:        int32(limit),
		Offset:       int32(offset),
	}

	resp, err := j.client.GetManualJournal(ctx, req)
	if err != nil {
		return nil, 0, err
	}
	if resp == nil {
		return nil, 0, nil
	}

	entries := resp.GetEntries()
	facts := make([]tradingplan.ManualTradeFact, 0, len(entries))
	for _, e := range entries {
		if e == nil {
			continue
		}
		facts = append(facts, tradingplan.ManualTradeFact{
			TradeID:       e.GetTradeId(),
			Symbol:        e.GetSymbol(),
			Direction:     e.GetDirection(),
			TradingStyle:  e.GetTradingStyle(),
			SetupType:     e.GetSetupType(),
			EntryPrice:    e.GetEntryPrice(),
			StopLoss:      e.GetStopLoss(),
			TP1Price:      e.GetTp1Price(),
			TP2Price:      e.GetTp2Price(),
			TP3Price:      e.GetTp3Price(),
			ExitPrice:     e.GetExitPrice(),
			RiskPercent:   e.GetRiskPercent(),
			TotalLotSize:  e.GetTotalLotSize(),
			RRRatio:       e.GetRrRatio(),
			RMultiple:     e.GetRMultiple(),
			GrossPnL:      e.GetGrossPnl(),
			Outcome:       e.GetOutcome(),
			Session:       e.GetSession(),
			IsOpen:        e.GetIsOpen(),
			OpenedAt:      e.GetOpenedAt(),
			ClosedAt:      e.GetClosedAt(),
			BrokerOrderID: e.GetBrokerOrderId(),
		})
	}
	return facts, int(resp.GetTotalClosed()), nil
}

// rfc3339OrEmpty renders a time as RFC3339, or "" when it is the zero
// time (the management handler treats an empty bound as unbounded).
func rfc3339OrEmpty(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.UTC().Format(time.RFC3339)
}
