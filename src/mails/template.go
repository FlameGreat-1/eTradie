package mails

import (
	"crypto/rand"
	"encoding/hex"
	"strings"
)

// generateID produces a 16-byte (32 hex char) random identifier,
// matching the auth package's GenerateID convention.
func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// WaitlistWelcomeHTML returns the branded HTML email sent to users
// who join the Exoper waitlist. The email address is interpolated
// into the template body.
func WaitlistWelcomeHTML(recipientEmail string) string {
	return strings.ReplaceAll(waitlistTemplate, "{{EMAIL}}", recipientEmail)
}

const waitlistTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Welcome to Exoper</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a;">
<tr><td align="center" style="padding: 20px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#111111;border-radius:16px;border:1px solid rgba(255,255,255,0.06);overflow:hidden;margin: 0 auto;">

  <!-- Header with Logo -->
  <tr><td style="padding:40px 40px 24px 40px;text-align:center;">
    <img src="https://exoper.com/assets/sidebar/icons/logo.png" alt="Exoper" width="48" height="48" style="display:inline-block;vertical-align:middle;" />
    <span style="display:inline-block;vertical-align:middle;margin-left:12px;font-size:24px;font-weight:700;color:#ffffff;letter-spacing:-0.03em;">Exoper</span>
  </td></tr>

  <!-- Divider -->
  <tr><td style="padding:0 40px;">
    <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent);"></div>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:32px 40px;">
    <h1 style="margin:0 0 16px 0;font-size:26px;font-weight:700;color:#ffffff;line-height:1.3;letter-spacing:-0.02em;">
      You're on the list.
    </h1>
    <p style="margin:0 0 20px 0;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.7);">
      Thanks for joining the Exoper waitlist. We're building something different for the retail trading community — a platform where you trade with structure, precision, and confidence.
    </p>
    <p style="margin:0 0 20px 0;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.7);">
      Exoper combines institutional-grade technical analysis with AI-powered execution. No guesswork. No emotional trading. Just disciplined, data-driven decisions executed with speed.
    </p>
    <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.7);">
      Stay tuned — we've got something exceptional in store for you.
    </p>
  </td></tr>

  <!-- CTA Button -->
  <tr><td style="padding:0 40px 32px 40px;text-align:center;">
    <a href="https://exoper.com" target="_blank" style="display:inline-block;padding:14px 36px;background-color:#ff6b00;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;border-radius:10px;letter-spacing:0.02em;">
      Visit Exoper
    </a>
  </td></tr>

  <!-- Divider -->
  <tr><td style="padding:0 40px;">
    <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.06),transparent);"></div>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:24px 40px 32px 40px;text-align:center;">
    <p style="margin:0 0 8px 0;font-size:12px;color:rgba(255,255,255,0.35);line-height:1.6;">
      This email was sent to <span style="color:rgba(255,255,255,0.5);">{{EMAIL}}</span> because you joined the Exoper waitlist.
    </p>
    <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.25);line-height:1.6;">
      &copy; 2025 Exoper. All rights reserved.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>`
