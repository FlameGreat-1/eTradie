package analytics

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// AlertTransport defines the publisher needed to dispatch reports.
type AlertTransport interface {
	Publish(ctx context.Context, event *alert.Event)
}

// Reporter generates and dispatches periodic performance summary reports.
type Reporter struct {
	metrics   *Metrics
	transport AlertTransport
	log       zerolog.Logger
}

// NewReporter creates a report generator.
func NewReporter(metrics *Metrics, transport AlertTransport) *Reporter {
	return &Reporter{
		metrics:   metrics,
		transport: transport,
		log:       observability.Logger("analytics_reporter"),
	}
}

// GenerateWeeklyReport compiles performance for the past week and sends it via alert dispatcher.
func (r *Reporter) GenerateWeeklyReport(ctx context.Context) error {
	return r.generateAndSend(ctx, "WEEKLY", "Weekly Performance Report")
}

// GenerateMonthlyReport compiles performance for the past month and sends it via alert dispatcher.
func (r *Reporter) GenerateMonthlyReport(ctx context.Context) error {
	return r.generateAndSend(ctx, "MONTHLY", "Monthly Performance Report")
}

func (r *Reporter) generateAndSend(ctx context.Context, period, title string) error {
	summary, err := r.metrics.Calculate(ctx, period)
	if err != nil {
		r.log.Error().Err(err).Str("period", period).Msg("failed_to_calculate_report")
		return fmt.Errorf("calculate %s metrics: %w", period, err)
	}

	if summary.TotalTrades == 0 {
		r.log.Info().Str("period", period).Msg("no_trades_for_report")
		return nil // Nothing to report
	}

	msg := fmt.Sprintf("%s\nTrades: %d | Win Rate: %.1f%%\nTotal PnL: $%.2f | Avg R: %.2f\nStreaks: %dW : %dL",
		title,
		summary.TotalTrades, summary.WinRate, summary.TotalPnL, summary.AvgRMultiple,
		summary.MaxConsecutiveWins, summary.MaxConsecutiveLosses)

	// Dispatch the report via standard alerting transport (goes to Telegram/Discord).
	r.transport.Publish(ctx, alert.NewEvent(
		alert.SourceTradeManager,
		alert.TypePerformanceReport,
		alert.SeverityInfo,
		msg,
	).WithDetails(map[string]interface{}{
		"win_rate":     summary.WinRate,
		"pnl":          summary.TotalPnL,
		"total_trades": summary.TotalTrades,
		"expectancy":   summary.Expectancy,
	}))

	r.log.Info().Str("period", period).Msg("report_generated_and_sent")
	return nil
}
