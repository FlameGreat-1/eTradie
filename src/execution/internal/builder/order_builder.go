package builder

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
)

// Build constructs a complete Order from a validated TradeRequest
// and SizingResult. Determines execution mode from config.
func Build(
	req *models.TradeRequest,
	sizing *models.SizingResult,
	cfg *config.Config,
) *models.Order {
	now := time.Now().UTC()
	mode := cfg.ExecutionMode()
	orderID := generateOrderID(req.Symbol, now)
	entryPrice := req.EntryPrice()

	order := &models.Order{
		OrderID:        orderID,
		Symbol:         req.Symbol,
		Direction:      req.Direction,
		ExecutionMode:  mode,
		EntryPrice:     entryPrice,
		StopLoss:       req.StopLoss,
		TP1Price:       req.TP1Price,
		TP1Pct:         req.TP1Pct,
		TP2Price:       req.TP2Price,
		TP2Pct:         req.TP2Pct,
		TP3Price:       req.TP3Price,
		TP3Pct:         req.TP3Pct,
		LotSize:        sizing.LotSize,
		RiskPercent:    req.RiskPercentage,
		RiskAmount:     sizing.RiskAmount,
		RRRatio:        req.RRRatio,
		AccountBalance: sizing.AccountBalance,
		SLDistancePips: sizing.SLDistancePips,
		PipValue:       sizing.PipValue,
		AnalysisID:     req.AnalysisID,
		TradingStyle:   req.TradingStyle,
		Session:        req.Session,
		Grade:          req.Grade,
		Confluence:     req.ConfluenceScore,
		Confidence:     req.Confidence,
		CreatedAt:      now,
	}

	switch mode {
	case constants.ModeLimit:
		ttl, ok := constants.LimitTTLCandlesByStyle[req.TradingStyle]
		if !ok {
			ttl = constants.LimitTTLCandlesByStyle[constants.StyleIntraday]
		}
		order.TTLCandles = ttl

	case constants.ModeInstant:
		order.WatcherID = fmt.Sprintf("GRT_%s_%s", req.Symbol, orderID[4:])
		order.OvershootTolerance = req.EntryZoneWidth() * cfg.OvershootToleranceMultiplier
	}

	return order
}

func generateOrderID(symbol string, t time.Time) string {
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return fmt.Sprintf("ORD_%s_%s_%s",
		symbol,
		t.Format("20060102_150405"),
		hex.EncodeToString(b),
	)
}
