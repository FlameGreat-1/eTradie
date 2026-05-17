package performancereview

import (
	"fmt"
	"strings"
	"time"
)

// ValidationError mirrors tradingplan.ValidationError so the SPA
// reuses the same field-level error renderer.
type ValidationError struct {
	Message string            `json:"message"`
	Fields  map[string]string `json:"fields,omitempty"`
}

func (e *ValidationError) Error() string { return e.Message }

func newValidationError(msg string) *ValidationError {
	return &ValidationError{Message: msg, Fields: make(map[string]string)}
}

func (e *ValidationError) add(field, msg string) *ValidationError {
	e.Fields[field] = msg
	return e
}

func (e *ValidationError) hasFields() bool { return len(e.Fields) > 0 }

// Bounds chosen to keep the review readable on a single mobile screen
// per section while leaving room for genuine analytical content. The
// upper bounds also bound the JSONB payload size: at the maxima a
// single review serialises to ~30 KB which is well under the 512 KB
// callback ceiling (see store.go and handlers.go).
const (
	headlineMax       = 160
	narrativeMax      = 1200
	shortNarrativeMax = 600

	bulletMin         = 0
	bulletMax         = 12
	bulletLenMax      = 280

	recMin            = 3
	recMax            = 10
	recLenMax         = 280

	focusMin          = 3
	focusMax          = 8
	focusLenMax       = 240

	adherenceMin      = 0
	adherenceMax      = 12
	adherenceLabelMax = 80
	adherenceValueMax = 24

	setupMin          = 0
	setupMax          = 12
	setupLabelMax     = 80
	setupValueMax     = 24

	sessionMin        = 0
	sessionMax        = 8
	sessionLabelMax   = 60
	sessionValueMax   = 120

	evolutionMax      = 12
	evolutionLabelMax = 80
	evolutionValueMax = 24

	warningMax        = 8
	warningSignalMax  = 80
	warningExplainMax = 360

	metricFieldMax    = 64
)

// bannedPhrases are the guru / motivational / fortune-telling phrases
// PLAN.md explicitly forbids ('Most Important Architectural Decision').
// Defense-in-depth: the system prompt already instructs the LLM to
// avoid them, but the validator rejects any payload that slips through
// before persistence so the user never sees them.
var bannedPhrases = []string{
	"guaranteed return",
	"guaranteed profit",
	"risk-free",
	"risk free",
	"double your",
	"triple your",
	"10x your",
	"100x your",
	"will make $",
	"will generate $",
	"no losses",
	"zero risk",
	"you got this",
	"crush it",
	"to the moon",
	"diamond hands",
}

func containsBannedPhrase(s string) (string, bool) {
	lower := strings.ToLower(s)
	for _, p := range bannedPhrases {
		if strings.Contains(lower, p) {
			return p, true
		}
	}
	return "", false
}

func trimString(s string, max int) string {
	s = strings.TrimSpace(s)
	if max > 0 && len(s) > max {
		s = s[:max]
	}
	return s
}

// cleanList trims, drops empties, drops banned phrases, dedupes
// case-insensitively, and caps to max. Returns the cleaned slice and
// the first banned phrase (if any) so the caller can surface a field
// error. Order-preserving.
func cleanList(in []string, lenMax, listMax int, fieldLabel string, errs *ValidationError) []string {
	out := make([]string, 0, len(in))
	seen := make(map[string]bool, len(in))
	for _, raw := range in {
		item := trimString(raw, lenMax)
		if item == "" {
			continue
		}
		if phrase, ok := containsBannedPhrase(item); ok {
			errs.add(fieldLabel,
				fmt.Sprintf("banned phrase %q not allowed in a performance review", phrase))
			continue
		}
		lower := strings.ToLower(item)
		if seen[lower] {
			continue
		}
		seen[lower] = true
		out = append(out, item)
	}
	if listMax > 0 && len(out) > listMax {
		out = out[:listMax]
	}
	return out
}

// Validate enforces the structural and ethical guardrails on a Review
// before it is persisted. Mutates the review in place to trim and
// normalise inputs so callers can store the cleaned value directly.
//
// Used by:
//   - the engine callback handler (validates LLM output before save),
//   - the user-facing PUT handler  (none defined yet, but the shape
//     is reserved for a future 'archive note' edit endpoint).
func Validate(r *Review) error {
	if r == nil {
		return newValidationError("review is required")
	}
	errs := newValidationError("performance review is invalid")

	// -- Period + window ------------------------------------------------
	if !r.Period.IsValid() {
		errs.add("period", "period must be 'weekly' or 'monthly'")
	}
	if r.PeriodStart.IsZero() {
		errs.add("period_start", "period_start is required")
	}
	if r.PeriodEnd.IsZero() {
		errs.add("period_end", "period_end is required")
	}
	if !r.PeriodStart.IsZero() && !r.PeriodEnd.IsZero() && r.PeriodEnd.Before(r.PeriodStart) {
		errs.add("period_end", "period_end must be on or after period_start")
	}

	// -- Section 1: Executive Summary -----------------------------------
	r.ExecutiveSummary.Headline = trimString(r.ExecutiveSummary.Headline, headlineMax)
	r.ExecutiveSummary.Narrative = trimString(r.ExecutiveSummary.Narrative, narrativeMax)
	if r.ExecutiveSummary.Headline == "" {
		errs.add("executive_summary.headline", "headline is required")
	}
	if r.ExecutiveSummary.Narrative == "" {
		errs.add("executive_summary.narrative", "narrative is required")
	}
	if phrase, ok := containsBannedPhrase(r.ExecutiveSummary.Headline); ok {
		errs.add("executive_summary.headline",
			fmt.Sprintf("banned phrase %q not allowed", phrase))
	}
	if phrase, ok := containsBannedPhrase(r.ExecutiveSummary.Narrative); ok {
		errs.add("executive_summary.narrative",
			fmt.Sprintf("banned phrase %q not allowed", phrase))
	}

	// -- Section 2: Performance Metrics ---------------------------------
	r.PerformanceMetrics.TotalTrades = trimString(r.PerformanceMetrics.TotalTrades, metricFieldMax)
	r.PerformanceMetrics.WinRate = trimString(r.PerformanceMetrics.WinRate, metricFieldMax)
	r.PerformanceMetrics.AvgRR = trimString(r.PerformanceMetrics.AvgRR, metricFieldMax)
	r.PerformanceMetrics.NetPnL = trimString(r.PerformanceMetrics.NetPnL, metricFieldMax)
	r.PerformanceMetrics.BestSession = trimString(r.PerformanceMetrics.BestSession, metricFieldMax)
	r.PerformanceMetrics.WorstSession = trimString(r.PerformanceMetrics.WorstSession, metricFieldMax)
	r.PerformanceMetrics.MostProfitableSetup = trimString(r.PerformanceMetrics.MostProfitableSetup, metricFieldMax)
	r.PerformanceMetrics.WorstBehavior = trimString(r.PerformanceMetrics.WorstBehavior, metricFieldMax)
	if r.PerformanceMetrics.TotalTrades == "" {
		errs.add("performance_metrics.total_trades", "total_trades is required")
	}

	// -- Section 3: Behavioral Analysis ---------------------------------
	r.BehavioralAnalysis.Patterns = cleanList(
		r.BehavioralAnalysis.Patterns,
		bulletLenMax, bulletMax,
		"behavioral_analysis.patterns", errs,
	)
	_ = bulletMin // explicit lower bound is 0 for low-confidence rows

	// -- Section 4: System Adherence ------------------------------------
	cleanedAdh := make([]AdherenceItem, 0, len(r.SystemAdherence.Items))
	seenAdh := make(map[string]bool, len(r.SystemAdherence.Items))
	for _, it := range r.SystemAdherence.Items {
		item := AdherenceItem{
			Rule:       trimString(it.Rule, adherenceLabelMax),
			Compliance: trimString(it.Compliance, adherenceValueMax),
		}
		if item.Rule == "" {
			continue
		}
		lower := strings.ToLower(item.Rule)
		if seenAdh[lower] {
			continue
		}
		seenAdh[lower] = true
		cleanedAdh = append(cleanedAdh, item)
	}
	if len(cleanedAdh) > adherenceMax {
		cleanedAdh = cleanedAdh[:adherenceMax]
	}
	r.SystemAdherence.Items = cleanedAdh

	// -- Section 5: Emotional Intelligence -----------------------------
	r.EmotionalIntelligence.Narrative = trimString(r.EmotionalIntelligence.Narrative, narrativeMax)
	if phrase, ok := containsBannedPhrase(r.EmotionalIntelligence.Narrative); ok {
		errs.add("emotional_intelligence.narrative",
			fmt.Sprintf("banned phrase %q not allowed", phrase))
	}

	// -- Section 6: Setup Quality ---------------------------------------
	cleanedSetups := make([]SetupQualityItem, 0, len(r.SetupQuality.Items))
	seenSetup := make(map[string]bool, len(r.SetupQuality.Items))
	for _, it := range r.SetupQuality.Items {
		item := SetupQualityItem{
			Setup:   trimString(it.Setup, setupLabelMax),
			WinRate: trimString(it.WinRate, setupValueMax),
			AvgRR:   trimString(it.AvgRR, setupValueMax),
		}
		if item.Setup == "" {
			continue
		}
		lower := strings.ToLower(item.Setup)
		if seenSetup[lower] {
			continue
		}
		seenSetup[lower] = true
		cleanedSetups = append(cleanedSetups, item)
	}
	if len(cleanedSetups) > setupMax {
		cleanedSetups = cleanedSetups[:setupMax]
	}
	r.SetupQuality.Items = cleanedSetups

	// -- Section 7: Session Analysis ------------------------------------
	cleanedSess := make([]SessionItem, 0, len(r.SessionAnalysis.Items))
	seenSess := make(map[string]bool, len(r.SessionAnalysis.Items))
	for _, it := range r.SessionAnalysis.Items {
		item := SessionItem{
			Session:     trimString(it.Session, sessionLabelMax),
			Performance: trimString(it.Performance, sessionValueMax),
		}
		if item.Session == "" {
			continue
		}
		lower := strings.ToLower(item.Session)
		if seenSess[lower] {
			continue
		}
		seenSess[lower] = true
		cleanedSess = append(cleanedSess, item)
	}
	if len(cleanedSess) > sessionMax {
		cleanedSess = cleanedSess[:sessionMax]
	}
	r.SessionAnalysis.Items = cleanedSess

	// -- Section 8: Risk Analysis ---------------------------------------
	r.RiskAnalysis.Narrative = trimString(r.RiskAnalysis.Narrative, shortNarrativeMax)
	if phrase, ok := containsBannedPhrase(r.RiskAnalysis.Narrative); ok {
		errs.add("risk_analysis.narrative",
			fmt.Sprintf("banned phrase %q not allowed", phrase))
	}

	// -- Section 9: Improvement Recommendations -------------------------
	r.ImprovementRecommendations.Items = cleanList(
		r.ImprovementRecommendations.Items,
		recLenMax, recMax,
		"improvement_recommendations.items", errs,
	)
	// recMin is enforced only when the confidence band allows it
	// (low/insufficient may legitimately have zero recommendations).
	if r.ConfidenceReport.Band == ConfidenceHigh ||
		r.ConfidenceReport.Band == ConfidenceMedium {
		if len(r.ImprovementRecommendations.Items) < recMin {
			errs.add("improvement_recommendations.items",
				fmt.Sprintf("need at least %d recommendations at this confidence band (got %d)",
					recMin, len(r.ImprovementRecommendations.Items)))
		}
	}

	// -- Section 10: Next Period Focus ---------------------------------
	r.NextFocus.Items = cleanList(
		r.NextFocus.Items,
		focusLenMax, focusMax,
		"next_focus.items", errs,
	)
	if r.ConfidenceReport.Band == ConfidenceHigh ||
		r.ConfidenceReport.Band == ConfidenceMedium {
		if len(r.NextFocus.Items) < focusMin {
			errs.add("next_focus.items",
				fmt.Sprintf("need at least %d focus areas at this confidence band (got %d)",
					focusMin, len(r.NextFocus.Items)))
		}
	}

	// -- Section 11: Confidence Report ----------------------------------
	if !r.ConfidenceReport.Band.IsValid() {
		errs.add("confidence_report.band",
			"confidence band must be one of: high, medium, low, insufficient")
	}
	if r.ConfidenceReport.SampleSize < 0 {
		errs.add("confidence_report.sample_size", "sample_size cannot be negative")
	}
	r.ConfidenceReport.Note = trimString(r.ConfidenceReport.Note, shortNarrativeMax)

	// -- Section 12: Trader Evolution -----------------------------------
	cleanedEv := make([]EvolutionDelta, 0, len(r.TraderEvolution.Items))
	seenEv := make(map[string]bool, len(r.TraderEvolution.Items))
	for _, it := range r.TraderEvolution.Items {
		item := EvolutionDelta{
			Metric:    trimString(it.Metric, evolutionLabelMax),
			Direction: trimString(strings.ToLower(it.Direction), evolutionValueMax),
			Delta:     trimString(it.Delta, evolutionValueMax),
		}
		if item.Metric == "" {
			continue
		}
		if item.Direction != "improved" && item.Direction != "declined" && item.Direction != "stable" {
			item.Direction = "stable"
		}
		lower := strings.ToLower(item.Metric)
		if seenEv[lower] {
			continue
		}
		seenEv[lower] = true
		cleanedEv = append(cleanedEv, item)
	}
	if len(cleanedEv) > evolutionMax {
		cleanedEv = cleanedEv[:evolutionMax]
	}
	r.TraderEvolution.Items = cleanedEv

	// -- Section 13: System Alignment ----------------------------------
	r.SystemAlignment.Narrative = trimString(r.SystemAlignment.Narrative, narrativeMax)
	r.SystemAlignment.Gaps = cleanList(
		r.SystemAlignment.Gaps,
		bulletLenMax, bulletMax,
		"system_alignment.gaps", errs,
	)

	// -- Section 14: Psychological Warnings -----------------------------
	cleanedWarn := make([]PsychologicalWarning, 0, len(r.PsychologicalWarnings.Items))
	seenWarn := make(map[string]bool, len(r.PsychologicalWarnings.Items))
	for _, it := range r.PsychologicalWarnings.Items {
		item := PsychologicalWarning{
			Signal:      trimString(it.Signal, warningSignalMax),
			Severity:    trimString(strings.ToLower(it.Severity), 16),
			Explanation: trimString(it.Explanation, warningExplainMax),
		}
		if item.Signal == "" {
			continue
		}
		if item.Severity != "info" && item.Severity != "warning" && item.Severity != "critical" {
			item.Severity = "info"
		}
		lower := strings.ToLower(item.Signal)
		if seenWarn[lower] {
			continue
		}
		seenWarn[lower] = true
		cleanedWarn = append(cleanedWarn, item)
	}
	if len(cleanedWarn) > warningMax {
		cleanedWarn = cleanedWarn[:warningMax]
	}
	r.PsychologicalWarnings.Items = cleanedWarn

	// -- Footer fields --------------------------------------------------
	if r.GeneratedBy == "" {
		r.GeneratedBy = "Exoper AI"
	}
	if r.GeneratedAt.IsZero() {
		r.GeneratedAt = time.Now().UTC()
	}

	// Schema version is always overwritten with the package's current
	// value: the validator is the authoritative writer.
	r.SchemaVersion = CurrentSchemaVersion

	if errs.hasFields() {
		return errs
	}
	return nil
}
