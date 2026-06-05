package validator

import (
	"fmt"

	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

func pass() models.ValidationResult {
	return models.ValidationResult{Passed: true}
}

func reject(check constants.ValidationCheck, reason string) models.ValidationResult {
	return models.ValidationResult{
		Passed:      false,
		FailedCheck: check,
		Outcome:     constants.OutcomeReject,
		Reason:      reason,
	}
}

func queue(check constants.ValidationCheck, reason string) models.ValidationResult {
	return models.ValidationResult{
		Passed:      false,
		FailedCheck: check,
		Outcome:     constants.OutcomeQueue,
		Reason:      reason,
	}
}

func lock(check constants.ValidationCheck, reason string) models.ValidationResult {
	return models.ValidationResult{
		Passed:      false,
		FailedCheck: check,
		Outcome:     constants.OutcomeLock,
		Reason:      reason,
	}
}

func pause(check constants.ValidationCheck, reason string) models.ValidationResult {
	return models.ValidationResult{
		Passed:      false,
		FailedCheck: check,
		Outcome:     constants.OutcomePause,
		Reason:      reason,
	}
}

// halted reports a placement blocked by the global or per-user kill
// switch. Mirrors lock()/pause() but emits OutcomeHalted so the gRPC
// layer can map it to StatusHalted and a dedicated alert.
// CHECKLIST Section 8 (Kill Switches).
func halted(check constants.ValidationCheck, reason string) models.ValidationResult {
	return models.ValidationResult{
		Passed:      false,
		FailedCheck: check,
		Outcome:     constants.OutcomeHalted,
		Reason:      reason,
	}
}

func checkLabel(c constants.ValidationCheck) string {
	return fmt.Sprintf("check_%d", int32(c))
}
