package support

import (
	"fmt"
	"html"
	"strings"
)

// Outbound email templates. Every user-controlled field is run
// through html.EscapeString so a malicious subject / body cannot
// inject arbitrary markup into the rendered email.
//
// The templates intentionally avoid external CSS and remote images
// (other than the logo) so they render correctly across Gmail,
// Outlook, Apple Mail, and most enterprise webmail clients without
// surprises.

const emailFooterHTML = `
  <tr>
    <td style="padding: 24px 32px; border-top: 1px solid #1f2937; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 12px; line-height: 1.5; color: #6b7280;">
      <p style="margin: 0 0 8px 0;">You are receiving this email because of activity on an Exoper support ticket.</p>
      <p style="margin: 0;">&copy; Exoper. All rights reserved.</p>
    </td>
  </tr>
`

func emailShell(headerTitle, mainHTML string) string {
	return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>` + html.EscapeString(headerTitle) + `</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0a0a0a;">
    <tr>
      <td align="center" style="padding: 32px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;background-color:#111827;border:1px solid #1f2937;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding: 24px 32px; border-bottom: 1px solid #1f2937;">
              <span style="display:inline-block;font-size:18px;font-weight:700;color:#ffffff;letter-spacing:-0.01em;">Exoper</span>
              <span style="display:inline-block;margin-left:12px;font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;">Support</span>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 32px; color: #e5e7eb; font-size: 14px; line-height: 1.6;">
              ` + mainHTML + `
            </td>
          </tr>
          ` + emailFooterHTML + `
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`
}

func renderField(label, value string) string {
	return `<tr><td style="padding:4px 12px 4px 0;color:#9ca3af;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;">` +
		html.EscapeString(label) +
		`</td><td style="padding:4px 0;color:#e5e7eb;font-size:13px;">` +
		html.EscapeString(value) +
		`</td></tr>`
}

func renderMetaTable(rows ...string) string {
	return `<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px 0;">` +
		strings.Join(rows, "") +
		`</table>`
}

func renderBodyBlock(body string) string {
	escaped := html.EscapeString(body)
	escaped = strings.ReplaceAll(escaped, "\n", "<br>")
	return `<div style="margin:16px 0;padding:16px;background-color:#0f172a;border:1px solid #1f2937;border-radius:8px;font-size:13px;line-height:1.6;color:#e5e7eb;white-space:normal;">` +
		escaped +
		`</div>`
}

func renderButton(label, href string) string {
	return `<div style="margin:24px 0;">
      <a href="` + html.EscapeString(href) + `" style="display:inline-block;background-color:#2563eb;color:#ffffff;text-decoration:none;padding:10px 18px;border-radius:8px;font-weight:600;font-size:13px;">` +
		html.EscapeString(label) +
		`</a>
    </div>`
}

// dashboardLinkFor renders the dashboard URL for a given ticket. If
// the ticket has no signed-in owner (anonymous contact form), the
// link points at the public site root instead.
func dashboardLinkFor(t *Ticket, siteURL string) string {
	if t.UserID == nil {
		return siteURL
	}
	return fmt.Sprintf("%s/dashboard/support?ticket=%s", siteURL, t.ID)
}

// newTicketStaffHTML renders the inbox notification sent to the
// staff inbox when a brand-new ticket is opened.
func newTicketStaffHTML(t *Ticket, siteURL string) string {
	name := t.Name
	if name == "" {
		name = "(not provided)"
	}
	body := ""
	if len(t.Messages) > 0 {
		body = t.Messages[0].Body
	}

	main := `
    <h1 style="margin:0 0 8px 0;font-size:18px;font-weight:700;color:#ffffff;">New support ticket</h1>
    <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">A new ticket has just been opened on the Exoper platform.</p>
    ` + renderMetaTable(
		renderField("Reference", t.PublicRef),
		renderField("From", t.Email),
		renderField("Name", name),
		renderField("Subject", t.Subject),
		renderField("Category", string(t.Category)),
		renderField("Priority", string(t.Priority)),
		renderField("Channel", string(t.Channel)),
	) + `
    <p style="margin:24px 0 8px 0;font-size:13px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.04em;">Message</p>
    ` + renderBodyBlock(body) +
		renderButton("Open in dashboard", dashboardLinkFor(t, siteURL))

	return emailShell("New support ticket", main)
}

// newTicketUserHTML renders the acknowledgement sent to the user who
// just opened a ticket.
func newTicketUserHTML(t *Ticket, siteURL string) string {
	body := ""
	if len(t.Messages) > 0 {
		body = t.Messages[0].Body
	}
	main := `
    <h1 style="margin:0 0 8px 0;font-size:18px;font-weight:700;color:#ffffff;">We received your request</h1>
    <p style="margin:0 0 16px 0;font-size:13px;color:#d1d5db;line-height:1.6;">
      Thanks for getting in touch. Our team has been notified and will respond as soon as possible.
      Please keep this reference for your records:
    </p>
    ` + renderMetaTable(
		renderField("Reference", t.PublicRef),
		renderField("Subject", t.Subject),
		renderField("Category", string(t.Category)),
		renderField("Priority", string(t.Priority)),
	) + `
    <p style="margin:24px 0 8px 0;font-size:13px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.04em;">Your message</p>
    ` + renderBodyBlock(body) +
		renderButton("View ticket", dashboardLinkFor(t, siteURL)) + `
    <p style="margin:16px 0 0 0;font-size:12px;color:#6b7280;line-height:1.6;">
      If you did not open this ticket, please ignore this email.
    </p>`
	return emailShell("We received your request — "+t.PublicRef, main)
}

// newReplyStaffHTML renders the inbox notification sent on a user reply.
func newReplyStaffHTML(t *Ticket, m *Message, siteURL string) string {
	main := `
    <h1 style="margin:0 0 8px 0;font-size:18px;font-weight:700;color:#ffffff;">New reply on a support ticket</h1>
    <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">The user has just replied to an existing ticket.</p>
    ` + renderMetaTable(
		renderField("Reference", t.PublicRef),
		renderField("From", t.Email),
		renderField("Subject", t.Subject),
		renderField("Category", string(t.Category)),
		renderField("Priority", string(t.Priority)),
		renderField("Status", string(t.Status)),
	) + `
    <p style="margin:24px 0 8px 0;font-size:13px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.04em;">Reply</p>
    ` + renderBodyBlock(m.Body) +
		renderButton("Open in dashboard", dashboardLinkFor(t, siteURL))
	return emailShell("New reply on "+t.PublicRef, main)
}

// ticketClosedStaffHTML renders the inbox notification sent when a
// user closes their own ticket.
func ticketClosedStaffHTML(t *Ticket, siteURL string) string {
	main := `
    <h1 style="margin:0 0 8px 0;font-size:18px;font-weight:700;color:#ffffff;">Ticket closed by user</h1>
    <p style="margin:0 0 16px 0;font-size:13px;color:#9ca3af;">The user has closed this ticket.</p>
    ` + renderMetaTable(
		renderField("Reference", t.PublicRef),
		renderField("From", t.Email),
		renderField("Subject", t.Subject),
		renderField("Category", string(t.Category)),
		renderField("Priority", string(t.Priority)),
	) +
		renderButton("Open in dashboard", dashboardLinkFor(t, siteURL))
	return emailShell("Ticket closed — "+t.PublicRef, main)
}
