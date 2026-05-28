package mails

import (
	"fmt"
	"html"
	"strings"
)

// SoftCapWarningSubject is the canonical Subject: header used for the
// soft-cap warning email. Exported so the gateway metering handler can
// reference the same literal and a renaming is a compile-time check.
const SoftCapWarningSubject = "You're approaching your Exoper AI token limit"

// SoftCapWarningHTML composes the branded HTML email sent to a Pro Managed
// user the first time their monthly LLM token usage crosses the configured
// soft-cap threshold (default 80% of the monthly cap).
//
// All caller-supplied string values are HTML-escaped before interpolation
// so a malicious display name (which only ever comes from auth_users.username,
// but defence-in-depth) cannot smuggle markup into the message.
//
// Inputs:
//   - displayName        : user's username; rendered in the greeting.
//   - usagePercent       : the soft-cap percentage that was crossed
//                          (e.g. 80). Shown in the headline so the user
//                          immediately understands what changed.
//   - resetDateLabel     : human-readable date the monthly window
//                          resets, e.g. "15 June 2026". Computed by
//                          the caller from monthly_window_start +
//                          1 month, formatted for the user's locale.
//   - monthlyInputLimit  : the absolute monthly input-token cap. Shown
//                          for transparency so the user can plan.
//   - monthlyOutputLimit : the absolute monthly output-token cap.
//   - dashboardURL       : fully-qualified link to the SPA usage panel.
//                          The button in the email body opens this URL.
func SoftCapWarningHTML(
	displayName string,
	usagePercent int,
	resetDateLabel string,
	monthlyInputLimit, monthlyOutputLimit int64,
	dashboardURL string,
) string {
	safeName := html.EscapeString(strings.TrimSpace(displayName))
	if safeName == "" {
		safeName = "there"
	}
	safeResetDate := html.EscapeString(strings.TrimSpace(resetDateLabel))
	if safeResetDate == "" {
		safeResetDate = "the start of your next billing cycle"
	}
	safeDashboardURL := html.EscapeString(strings.TrimSpace(dashboardURL))

	// Replace the entire CTA block based on whether we have a usable
	// URL. An empty href would render as a broken-looking button in
	// every major email client. When the URL is missing, omit the
	// button entirely; the body text still carries the essential
	// warning information. Audit ref: ADMIN-QUOTA-AUDIT-V3-A11.
	ctaBlock := ""
	if safeDashboardURL != "" {
		ctaBlock = `<a href="` + safeDashboardURL + `" style="display:inline-block;padding:12px 24px;background-color:#3b82f6;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;border-radius:8px;">View usage dashboard</a>`
	}

	body := strings.ReplaceAll(softCapTemplate, "{{NAME}}", safeName)
	body = strings.ReplaceAll(body, "{{PERCENT}}", fmt.Sprintf("%d", usagePercent))
	body = strings.ReplaceAll(body, "{{RESET_DATE}}", safeResetDate)
	body = strings.ReplaceAll(body, "{{INPUT_LIMIT}}", formatTokens(monthlyInputLimit))
	body = strings.ReplaceAll(body, "{{OUTPUT_LIMIT}}", formatTokens(monthlyOutputLimit))
	body = strings.ReplaceAll(body, "{{CTA_BLOCK}}", ctaBlock)
	return body
}

// formatTokens renders a token-count limit in a human-friendly form:
// 1_500_000 -> "1.5M tokens", 20_000_000 -> "20M tokens", 750 -> "750 tokens".
// Used only by SoftCapWarningHTML; kept private to the file because there
// is no other caller and the rendering shape is template-specific.
func formatTokens(n int64) string {
	if n <= 0 {
		return "unlimited"
	}
	switch {
	case n >= 1_000_000:
		whole := n / 1_000_000
		frac := (n % 1_000_000) / 100_000
		if frac == 0 {
			return fmt.Sprintf("%dM tokens", whole)
		}
		return fmt.Sprintf("%d.%dM tokens", whole, frac)
	case n >= 1_000:
		return fmt.Sprintf("%dk tokens", n/1_000)
	default:
		return fmt.Sprintf("%d tokens", n)
	}
}

const softCapTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Approaching your AI token limit</title>
</head>
<body style="margin:0;padding:0;background-color:#0b0b0f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#e6e6ea;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#0b0b0f;">
    <tr>
      <td align="center" style="padding: 20px 0;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background-color:#141419;border:1px solid #25252d;border-radius:12px;overflow:hidden;margin: 0 auto;">
          <tr>
            <td style="padding:32px 32px 16px 32px;">
              <p style="margin:0 0 8px 0;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#f5a623;">Usage warning</p>
              <h1 style="margin:0;font-size:22px;line-height:1.3;color:#ffffff;font-weight:600;">You've used {{PERCENT}}% of your monthly AI tokens</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 16px 32px;">
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#c8c8d0;">Hi {{NAME}},</p>
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#c8c8d0;">Your Pro Managed subscription includes a monthly allowance of <strong style="color:#ffffff;">{{INPUT_LIMIT}}</strong> in and <strong style="color:#ffffff;">{{OUTPUT_LIMIT}}</strong> out for AI analysis. You have just crossed <strong style="color:#f5a623;">{{PERCENT}}% of one of those limits</strong>.</p>
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#c8c8d0;">Analyses will continue running normally for now. Your allowance resets on <strong style="color:#ffffff;">{{RESET_DATE}}</strong>. If you reach 100% before then, new analysis cycles will pause until the reset.</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:8px 32px 32px 32px;">
              {{CTA_BLOCK}}
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px 32px 32px;border-top:1px solid #25252d;">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#7a7a86;">You're receiving this email because you're on the Exoper Pro Managed plan and your AI token usage has crossed the configured warning threshold. You'll receive at most one warning email per billing cycle.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`
