// Package mails owns transactional email templates and SMTP delivery.
// Dependency direction note (audit finding L1): the auth package
// imports mails; this file adds the security-alert templates consumed
// by auth's anti-ATO notifications. Do NOT add an import of
// .../src/auth to this package (import cycle).
package mails

import (
	"fmt"
	"html"
	"strings"
)

// Subjects for the anti-ATO security notifications. Exported so the
// auth handler references the same literal and a rename is a
// compile-time check.
const (
	PasswordChangedSubject = "Your Exoper password was changed"
	NewLoginSubject        = "New sign-in to your Exoper account"
)

// securityMetaBlock renders the optional "when / origin / browser"
// footer shared by both security templates. Any empty field is shown
// as "unknown". All values are HTML-escaped.
func securityMetaBlock(whenUTC, ip, ua string) string {
	esc := func(s string) string {
		s = html.EscapeString(strings.TrimSpace(s))
		if s == "" {
			return "unknown"
		}
		return s
	}
	return fmt.Sprintf(
		`<p style="margin:16px 0 0;font-size:12px;line-height:1.7;color:#9aa0a6;">`+
			`Time: <span style="color:#cfd2d6;">%s</span><br>`+
			`Request origin: <span style="color:#cfd2d6;">%s</span><br>`+
			`Browser: <span style="color:#cfd2d6;">%s</span>`+
			`</p>`,
		esc(whenUTC), esc(ip), esc(ua),
	)
}

// PasswordChangedHTML composes the notification sent AFTER a user's
// password is changed (self-service change or reset redemption). It is
// informational: the change already happened. The value to the user is
// the "if this wasn't you" path, so the origin metadata is prominent.
func PasswordChangedHTML(displayName, whenUTC, ip, ua string) string {
	safeName := html.EscapeString(strings.TrimSpace(displayName))
	if safeName == "" {
		safeName = "there"
	}
	return fmt.Sprintf(
		securityAlertTemplate,
		"Your password was changed",
		safeName,
		"This is a confirmation that the password for your Exoper account was just changed. "+
			"You can keep using your account normally; for your security every other active session was signed out.",
		"If you did NOT make this change, your account may be compromised. "+
			"Reset your password immediately and contact support.",
		securityMetaBlock(whenUTC, ip, ua),
	)
}

// NewLoginHTML composes the notification sent when a successful login
// originates from a client IP not previously seen for this account.
func NewLoginHTML(displayName, whenUTC, ip, ua string) string {
	safeName := html.EscapeString(strings.TrimSpace(displayName))
	if safeName == "" {
		safeName = "there"
	}
	return fmt.Sprintf(
		securityAlertTemplate,
		"New sign-in detected",
		safeName,
		"We noticed a sign-in to your Exoper account from a device or location we have not seen before. "+
			"If this was you, no action is needed.",
		"If this was NOT you, change your password immediately \u2014 it secures your account and signs out every "+
			"other session \u2014 and contact support.",
		securityMetaBlock(whenUTC, ip, ua),
	)
}

// securityAlertTemplate is a real HTML document shared by both
// security notifications. fmt placeholders:
//   1: heading
//   2: safeName (greeting)
//   3: body paragraph (already trusted copy, no user data)
//   4: call-to-action paragraph (already trusted copy)
//   5: meta block (already HTML, from securityMetaBlock)
const securityAlertTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exoper security alert</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#e6e6e6;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#0a0a0a;">
    <tr>
      <td align="center" style="padding: 20px 0;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px;background-color:#111;border:1px solid #1f1f1f;border-radius:12px;padding:32px;margin: 0 auto;">
          <tr>
            <td style="padding-bottom:24px;">
              <span style="font-size:20px;font-weight:700;letter-spacing:-0.02em;color:#ffffff;">Exoper</span>
            </td>
          </tr>
          <tr>
            <td style="padding-bottom:8px;">
              <h1 style="margin:0;font-size:24px;line-height:1.3;font-weight:700;color:#ffffff;">%s</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 0 16px;">
              <p style="margin:0;font-size:15px;line-height:1.6;color:#cfd2d6;">Hi %s,</p>
              <p style="margin:12px 0 0;font-size:15px;line-height:1.6;color:#cfd2d6;">%s</p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 0 16px;">
              <p style="margin:0;font-size:14px;line-height:1.7;color:#f0b429;font-weight:600;">%s</p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 0 0;border-top:1px solid #1f1f1f;">
              %s
            </td>
          </tr>
          <tr>
            <td style="padding:24px 0 0;">
              <p style="margin:0;font-size:11px;line-height:1.6;color:#6b6f74;">
                &copy; Exoper. All rights reserved.<br>
                This is a security notification sent to protect your account.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`
