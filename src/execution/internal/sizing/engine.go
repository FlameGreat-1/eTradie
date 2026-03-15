package sizing

import (
	"context"
	"fmt"
	"math"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
)

// Engine calculates position size per Rulebook Section 7.1.
type Engine struct {
	cfg    *config.Config
	broker broker.Port
	log    zerolog.Logger
}

// NewEngine creates a position sizing engine.
func NewEngine(cfg *config.Config, bp broker.Port) *Engine {
	return &Engine{
		cfg:    cfg,
		broker: bp,
		log:    observability.Logger("sizing_engine"),
	}
}

// Calculate computes the lot size for a trade request.
// Fetches live balance and instrument info from the broker.
func (e *Engine) Calculate(ctx context.Context, req *models.TradeRequest) (*models.SizingResult, error) {
	start := time.Now()

	timeout := time.Duration(e.cfg.BrokerTimeoutMs) * time.Millisecond
	brokerCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	account, err := e.broker.GetAccountInfo(brokerCtx)
	if err != nil {
		return nil, fmt.Errorf("sizing: get account info: %w", err)
	}

	if account.Balance <= 0 {
		return nil, fmt.Errorf("sizing: account balance is %.2f, cannot size position", account.Balance)
	}

	info, err := e.broker.GetInstrumentInfo(brokerCtx, req.Symbol)
	if err != nil {
		return nil, fmt.Errorf("sizing: get instrument info for %s: %w", req.Symbol, err)
	}

	if info.PipSize <= 0 {
		return nil, fmt.Errorf("sizing: invalid pip size %.10f for %s", info.PipSize, req.Symbol)
	}
	if info.PipValue <= 0 {
		return nil, fmt.Errorf("sizing: invalid pip value %.10f for %s", info.PipValue, req.Symbol)
	}

	entryPrice := req.EntryPrice()
	slDistance := math.Abs(entryPrice - req.StopLoss)
	if slDistance <= 0 {
		return nil, fmt.Errorf("sizing: SL distance is zero (entry=%.5f, sl=%.5f)", entryPrice, req.StopLoss)
	}

	slPips := slDistance / info.PipSize
	if slPips <= 0 {
		return nil, fmt.Errorf("sizing: SL pips is zero after conversion")
	}

	riskAmount := account.Balance * (req.RiskPercentage / 100.0)
	lotSize := riskAmount / (slPips * info.PipValue)

	// Round to lot step.
	if info.LotStep > 0 {
		lotSize = math.Floor(lotSize/info.LotStep) * info.LotStep
	}

	// Apply lot size rounding to 2 decimal places.
	lotSize = math.Floor(lotSize*100) / 100

	// Enforce floor.
	minLot := e.cfg.MinLotSize
	if info.MinLotSize > minLot {
		minLot = info.MinLotSize
	}
	if lotSize < minLot {
		return nil, fmt.Errorf(
			"sizing: calculated lot size %.4f below minimum %.4f (balance=%.2f, risk=%.2f%%, sl_pips=%.1f)",
			lotSize, minLot, account.Balance, req.RiskPercentage, slPips,
		)
	}

	// Enforce ceiling.
	maxLot := e.cfg.MaxLotSize
	if info.MaxLotSize > 0 && info.MaxLotSize < maxLot {
		maxLot = info.MaxLotSize
	}
	if lotSize > maxLot {
		lotSize = maxLot
		riskAmount = lotSize * slPips * info.PipValue
	}

	result := &models.SizingResult{
		LotSize:        lotSize,
		RiskAmount:     math.Round(riskAmount*100) / 100,
		AccountBalance: account.Balance,
		SLDistancePips: math.Round(slPips*10) / 10,
		PipValue:       info.PipValue,
		PipSize:        info.PipSize,
	}

	elapsed := time.Since(start).Seconds()
	observability.SizingDuration.Observe(elapsed)
	observability.SizingLotSize.Observe(lotSize)

	e.log.Info().
		Str("symbol", req.Symbol).
		Float64("balance", account.Balance).
		Float64("risk_pct", req.RiskPercentage).
		Float64("risk_amount", result.RiskAmount).
		Float64("sl_pips", result.SLDistancePips).
		Float64("pip_value", info.PipValue).
		Float64("lot_size", lotSize).
		Str("grade", req.Grade).
		Str("analysis_id", req.AnalysisID).
		Str("trace_id", req.TraceID).
		Float64("duration_ms", elapsed*1000).
		Msg("lot_size_calculated")

	return result, nil
}
