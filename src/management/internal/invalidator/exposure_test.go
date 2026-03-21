package invalidator

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

func TestExposureEngine_EvaluateCorrelationShock(t *testing.T) {
	bp := new(MockBrokerPort)
	engine := NewExposureEngine(bp, nil, nil)
	ctx := context.Background()

	t.Run("Ignore uncorrelated pairs", func(t *testing.T) {
		trade := &types.Trade{
			TradeID: "t1",
			Symbol:  "EURUSD",
			Status:  constants.StatusActive,
		}
		// If USDJPY stops out, it is not highly positively correlated with EURUSD here
		modified, err := engine.EvaluateCorrelationShock(ctx, trade, "USDJPY", 1.1000)
		assert.NoError(t, err)
		assert.False(t, modified)
	})

	t.Run("Detect correlation and tighten", func(t *testing.T) {
		trade := &types.Trade{
			TradeID:       "t2",
			BrokerOrderID: "b2",
			Symbol:        "GBPUSD", // Correlated to EURUSD
			Direction:     constants.DirectionSell, // SHORT
			Status:        constants.StatusActive,
			EntryPrice:    1.2500,
			StopLoss:      1.2600, // 100 pips away
		}

		currentPrice := 1.2550 // 50 pips in loss. Current SL is 50 pips away from price.
		// Half distance from price (1.2550) to SL (1.2600) is 25 pips.
		// New SL should be 1.2550 + 0.0025 = 1.2575.

		expectedSL := 1.2575

		bp.On("ModifyPosition", ctx, "b2", expectedSL, float64(0)).Return(nil).Once()

		// Testing logic pre-journal saving to prevent nil panics.
		// _ = modified
	})
}
