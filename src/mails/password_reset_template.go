// Package mails owns transactional email templates and SMTP delivery.
// Dependency direction note (audit finding L1): the auth package
// imports mails (mails.Sender satisfies auth.Mailer; mails.PasswordResetHTML
// is composed by auth.handleForgotPassword). The arrow is therefore
// one-way: auth -> mails. Do NOT add `import ".../src/auth"` to any
// file in this package; doing so would introduce an import cycle that
// only manifests at `go build` time.
package mails

import (
	"fmt"
	"html"
	"strings"
)

// PasswordResetSubject is the canonical Subject: header used for the
// forgot-password email. Exported so the gateway handler can reference
// the same literal and a renaming is a compile-time check.
const PasswordResetSubject = "Reset your Exoper password"

// PasswordResetHTML composes the branded HTML email sent to a user who
// requests a password reset. All caller-supplied values are HTML-escaped
// before interpolation so a malicious display name (which only ever
// comes from auth_users.username, but defence-in-depth) cannot smuggle
// markup into the message.
//
// Inputs:
//   - displayName     : user's username; rendered in the greeting.
//   - resetURL        : fully-qualified link to the SPA reset page,
//                       including the single-use token as a query
//                       parameter (?token=...).
//   - expiresMinutes  : human-readable lifetime of the link. Shown
//                       prominently so the user does not procrastinate.
//   - requestIP       : optional IP that triggered the reset. Helps
//                       a security-conscious user spot foreign-origin
//                       resets. Empty string omits the line.
//   - requestUA       : optional User-Agent of the requester. Same
//                       rationale as requestIP.
func PasswordResetHTML(displayName, resetURL string, expiresMinutes int, requestIP, requestUA string) string {
	safeName := html.EscapeString(strings.TrimSpace(displayName))
	if safeName == "" {
		safeName = "there"
	}
	// resetURL is built server-side from a validated FrontendBaseURL +
	// a hex token, so it cannot contain HTML metacharacters; escape it
	// anyway because the attribute value lives next to user-controlled
	// data and the cost is zero.
	safeURL := html.EscapeString(resetURL)

	var requestMeta string
	if strings.TrimSpace(requestIP) != "" || strings.TrimSpace(requestUA) != "" {
		ip := html.EscapeString(strings.TrimSpace(requestIP))
		ua := html.EscapeString(strings.TrimSpace(requestUA))
		if ip == "" {
			ip = "unknown"
		}
		if ua == "" {
			ua = "unknown"
		}
		requestMeta = fmt.Sprintf(
			`<p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:#9aa0a6;">`+
				`Request origin: <span style="color:#cfd2d6;">%s</span><br>`+
				`Browser: <span style="color:#cfd2d6;">%s</span>`+
				`</p>`,
			ip, ua,
		)
	}

	body := fmt.Sprintf(passwordResetTemplate, safeName, safeURL, expiresMinutes, safeURL, requestMeta)
	return body
}

// passwordResetTemplate is a real HTML document (not entity-escaped)
// so MUAs render it as styled content. fmt placeholders:
//   1: safeName
//   2: safeURL  (used in the <a href> attribute)
//   3: expiresMinutes
//   4: safeURL  (rendered as plain-text fallback for clients that
//                strip the button)
//   5: requestMeta block (already HTML, may be empty)
const passwordResetTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset your Exoper password</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#e6e6e6;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#0a0a0a;">
    <tr>
      <td align="center" style="padding: 20px 0;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px;background-color:#111;border:1px solid #1f1f1f;border-radius:12px;padding:32px;margin: 0 auto;">
          <tr>
            <td style="padding-bottom:24px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <span style="font-size:20px;font-weight:700;letter-spacing:-0.02em;color:#ffffff;">Exoper</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding-bottom:8px;">
              <h1 style="margin:0;font-size:24px;line-height:1.3;font-weight:700;color:#ffffff;">
                Reset your password
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 0 16px;">
              <p style="margin:0;font-size:15px;line-height:1.6;color:#cfd2d6;">
                Hi %s,
              </p>
              <p style="margin:12px 0 0;font-size:15px;line-height:1.6;color:#cfd2d6;">
                We received a request to reset the password for your Exoper account. Click the button below to choose a new password. This link will expire in %[3]d minutes and can be used only once.
              </p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:16px 0 24px;">
              <a href="%[2]s" style="display:inline-block;padding:14px 28px;background-color:#76B900;color:#000000;text-decoration:none;font-weight:700;font-size:14px;letter-spacing:0.04em;border-radius:8px;">
                Reset Password
              </a>
            </td>
          </tr>
          <tr>
            <td style="padding:0 0 16px;">
              <p style="margin:0;font-size:13px;line-height:1.6;color:#9aa0a6;">
                If the button doesn't work, paste this URL into your browser:
              </p>
              <p style="margin:8px 0 0;font-size:13px;line-height:1.6;color:#cfd2d6;word-break:break-all;">
                <a href="%[4]s" style="color:#76B900;text-decoration:underline;">%[4]s</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 0 0;border-top:1px solid #1f1f1f;">
              <p style="margin:0;font-size:13px;line-height:1.6;color:#9aa0a6;">
                Didn't request this? You can safely ignore this email; your password will not change. If you didn't ask for a reset and you're seeing this, someone may have entered your email address by mistake.
              </p>
              %[5]s
            </td>
          </tr>
          <tr>
            <td style="padding:24px 0 0;">
              <p style="margin:0;font-size:11px;line-height:1.6;color:#6b6f74;">
                &copy; Exoper. All rights reserved.<br>
                This is a transactional email sent because a password reset was requested for your account.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`
