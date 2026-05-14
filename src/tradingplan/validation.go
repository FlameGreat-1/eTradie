package tradingplan

import (
	"fmt"
	"strings"
	"time"
)

// ValidationError mirrors tradingsystem.ValidationError so the SPA
// uses the same error renderer for both packages.
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

// Bounds chosen to keep the workbook printable on a single batch of
// pages while leaving room for a thorough plan. These match the
// PRACTICE.md examples and have been tested against representative
// LLM outputs.
const (
	profileBulletsMin    = 4
	profileBulletsMax    = 10
	profileBulletMaxLen  = 240
	profileHeadlineMax   = 160
	journalMaxRows       = 200
	journalCellMaxLen    = 120
	reviewPromptsMin     = 5
	reviewPromptsMax     = 12
	reviewPromptMaxLen   = 240
	scorecardItemsMin    = 3
	scorecardItemsMax    = 12
	scorecardLabelMaxLen = 80
	scorecardScoreMaxLen = 24
	objectivesMin        = 4
	objectivesMax        = 12
	objectiveMaxLen      = 240
	accountFieldMaxLen   = 64
	profileSummaryMaxLen = 280
)

// Banned substrings (lower-case match) that the system prompt
// forbids. PRACTICE.md is explicit that profit promises, guaranteed
// returns, and compounding fantasies are legally and ethically
// off-limits. We sanitise here as defense-in-depth: if a future
// prompt change weakens the constraint, the validator still rejects
// the offending payload before persistence.
var bannedPhrases = []string{
	"guaranteed return",
	"guaranteed profit",
	"risk-free",
	"risk free",
	"double your",
	"triple your",
	"10x your",
	"100x your",
	"turn $",
	"will make $",
	"will generate $",
	"profit guarantee",
	"no losses",
	"zero risk",
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

// Validate enforces the structural and ethical guardrails on a Plan
// before it is persisted. Mutates the plan in place to trim and
// normalise inputs so callers can store the cleaned value directly.
//
// Used by:
//   - the engine callback handler  (validates LLM output before save),
//   - the user-facing PUT handler  (validates manual edits).
//
// On success the plan's SchemaVersion and GeneratedAt are normalised.
func Validate(p *Plan) error {
	if p == nil {
		return newValidationError("plan is required")
	}
	errs := newValidationError("trading plan is invalid")

	// -- Section 1: Trader Profile -------------------------------------
	p.TraderProfile.Headline = trimString(p.TraderProfile.Headline, profileHeadlineMax)
	if p.TraderProfile.Headline == "" {
		errs.add("trader_profile.headline", "headline is required")
	}
	if phrase, ok := containsBannedPhrase(p.TraderProfile.Headline); ok {
		errs.add("trader_profile.headline",
			fmt.Sprintf("banned phrase %q not allowed in a trading plan", phrase))
	}
	cleanedBullets := make([]string, 0, len(p.TraderProfile.Bullets))
	for _, b := range p.TraderProfile.Bullets {
		b = trimString(b, profileBulletMaxLen)
		if b == "" {
			continue
		}
		if phrase, ok := containsBannedPhrase(b); ok {
			errs.add("trader_profile.bullets",
				fmt.Sprintf("banned phrase %q not allowed in a trading plan", phrase))
			continue
		}
		cleanedBullets = append(cleanedBullets, b)
	}
	if len(cleanedBullets) < profileBulletsMin {
		errs.add("trader_profile.bullets",
			fmt.Sprintf("need at least %d bullet points (got %d)", profileBulletsMin, len(cleanedBullets)))
	}
	if len(cleanedBullets) > profileBulletsMax {
		cleanedBullets = cleanedBullets[:profileBulletsMax]
	}
	p.TraderProfile.Bullets = cleanedBullets

	// -- Section 2: Account Parameters ---------------------------------
	p.Account.StartingBalance = trimString(p.Account.StartingBalance, accountFieldMaxLen)
	p.Account.MaxDailyRisk = trimString(p.Account.MaxDailyRisk, accountFieldMaxLen)
	p.Account.MaxWeeklyDrawdown = trimString(p.Account.MaxWeeklyDrawdown, accountFieldMaxLen)
	p.Account.PreferredRR = trimString(p.Account.PreferredRR, accountFieldMaxLen)
	p.Account.MaxTradesPerDay = trimString(p.Account.MaxTradesPerDay, accountFieldMaxLen)
	p.Account.TradingDaysPerWeek = trimString(p.Account.TradingDaysPerWeek, accountFieldMaxLen)

	if p.Account.StartingBalance == "" {
		errs.add("account.starting_balance", "starting balance is required")
	}
	if p.Account.MaxDailyRisk == "" {
		errs.add("account.max_daily_risk", "max daily risk is required")
	}
	if p.Account.PreferredRR == "" {
		errs.add("account.preferred_rr", "preferred RR is required")
	}

	// -- Section 3: Daily Execution Journal ----------------------------
	if len(p.Journal) > journalMaxRows {
		p.Journal = p.Journal[:journalMaxRows]
	}
	for i := range p.Journal {
		row := &p.Journal[i]
		row.Date = trimString(row.Date, journalCellMaxLen)
		row.Pair = trimString(row.Pair, journalCellMaxLen)
		row.Direction = trimString(row.Direction, journalCellMaxLen)
		row.Style = trimString(row.Style, journalCellMaxLen)
		row.Entry = trimString(row.Entry, journalCellMaxLen)
		row.Exit = trimString(row.Exit, journalCellMaxLen)
		row.RR = trimString(row.RR, journalCellMaxLen)
		row.PnL = trimString(row.PnL, journalCellMaxLen)
		row.Outcome = trimString(row.Outcome, journalCellMaxLen)
		row.Notes = trimString(row.Notes, journalCellMaxLen)
	}

	// -- Section 4: Weekly Review --------------------------------------
	cleanedPrompts := make([]string, 0, len(p.WeeklyReview.Prompts))
	for _, q := range p.WeeklyReview.Prompts {
		q = trimString(q, reviewPromptMaxLen)
		if q == "" {
			continue
		}
		if phrase, ok := containsBannedPhrase(q); ok {
			errs.add("weekly_review.prompts",
				fmt.Sprintf("banned phrase %q not allowed in a trading plan", phrase))
			continue
		}
		cleanedPrompts = append(cleanedPrompts, q)
	}
	if len(cleanedPrompts) < reviewPromptsMin {
		errs.add("weekly_review.prompts",
			fmt.Sprintf("need at least %d weekly review prompts (got %d)", reviewPromptsMin, len(cleanedPrompts)))
	}
	if len(cleanedPrompts) > reviewPromptsMax {
		cleanedPrompts = cleanedPrompts[:reviewPromptsMax]
	}
	p.WeeklyReview.Prompts = cleanedPrompts

	// -- Section 5: Discipline Scorecard -------------------------------
	cleanedScorecard := make([]DisciplineScorecardItem, 0, len(p.Scorecard.Items))
	seenMetrics := make(map[string]bool, len(p.Scorecard.Items))
	for _, item := range p.Scorecard.Items {
		item.Metric = trimString(item.Metric, scorecardLabelMaxLen)
		item.Score = trimString(item.Score, scorecardScoreMaxLen)
		if item.Metric == "" {
			continue
		}
		lowerMetric := strings.ToLower(item.Metric)
		if seenMetrics[lowerMetric] {
			continue
		}
		seenMetrics[lowerMetric] = true
		cleanedScorecard = append(cleanedScorecard, item)
	}
	if len(cleanedScorecard) < scorecardItemsMin {
		errs.add("scorecard.items",
			fmt.Sprintf("need at least %d scorecard metrics (got %d)", scorecardItemsMin, len(cleanedScorecard)))
	}
	if len(cleanedScorecard) > scorecardItemsMax {
		cleanedScorecard = cleanedScorecard[:scorecardItemsMax]
	}
	p.Scorecard.Items = cleanedScorecard

	// -- Section 6: 90-Day Objectives ----------------------------------
	cleanedObjectives := make([]string, 0, len(p.Objectives.Items))
	for _, o := range p.Objectives.Items {
		o = trimString(o, objectiveMaxLen)
		if o == "" {
			continue
		}
		if phrase, ok := containsBannedPhrase(o); ok {
			errs.add("objectives.items",
				fmt.Sprintf("banned phrase %q not allowed in a trading plan", phrase))
			continue
		}
		cleanedObjectives = append(cleanedObjectives, o)
	}
	if len(cleanedObjectives) < objectivesMin {
		errs.add("objectives.items",
			fmt.Sprintf("need at least %d objectives (got %d)", objectivesMin, len(cleanedObjectives)))
	}
	if len(cleanedObjectives) > objectivesMax {
		cleanedObjectives = cleanedObjectives[:objectivesMax]
	}
	p.Objectives.Items = cleanedObjectives

	// -- Footer fields --------------------------------------------------
	p.ProfileSummary = trimString(p.ProfileSummary, profileSummaryMaxLen)
	if p.GeneratedBy == "" {
		p.GeneratedBy = "Exoper AI"
	}
	if p.GeneratedAt.IsZero() {
		p.GeneratedAt = time.Now().UTC()
	}
	if p.BalanceCurrency == "" {
		p.BalanceCurrency = "USD"
	}

	// Schema version is always overwritten with the package's current
	// value: the validator is the authoritative writer, so a payload
	// from a future or past schema is normalised here.
	p.SchemaVersion = CurrentSchemaVersion

	if errs.hasFields() {
		return errs
	}
	return nil
}
