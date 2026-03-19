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

// BuildWithMode constructs a complete Order from a validated TradeRequest,
// SizingResult, and an explicitly provided execution mode. The mode is
// resolved by the caller (grpc_server reads it from the settings store
// so dashboard changes take effect immediately).
func BuildWithMode(
	req *models.TradeRequest,
	sizing *models.SizingResult,
	cfg *config.Config,
	mode constants.ExecutionMode,
) *models.Order {
	now := time.Now().UTC()
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
		SetupType:      req.SetupType,
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
		
		// If the Gateway already confirmed this setup (e.g. LTF structure existed 
		// at analysis time), we start the watcher in a pre-confirmed state.
		order.LTFConfirmed = req.LTFConfirmed
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
