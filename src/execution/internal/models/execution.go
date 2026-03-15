package models

import "github.com/flamegreat/etradie/src/execution/internal/constants"

// SizingResult holds the output of the position sizing engine.
type SizingResult struct {
	LotSize        float64
	RiskAmount     float64
	AccountBalance float64
	SLDistancePips float64
	PipValue       float64
	PipSize        float64
}

// ExecutionResult is what the execution service returns to the gateway.
type ExecutionResult struct {
	Accepted        bool
	Status          constants.OrderStatus
	OrderID         string
	RejectionReason string
	RejectionCheck  constants.ValidationCheck
	Order           *Order
}
