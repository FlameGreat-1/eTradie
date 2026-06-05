package mails

import (
	"strings"
	"testing"
)

func TestPasswordChangedHTML_EscapesAndRenders(t *testing.T) {
	out := PasswordChangedHTML(`<script>alert(1)</script>`, "Mon, 01 Jan 2026 00:00:00 UTC", "1.2.3.4", `Mozilla/5.0 <evil>`)
	if strings.Contains(out, "<script>alert(1)</script>") {
		t.Fatalf("display name was not escaped")
	}
	if strings.Contains(out, "<evil>") {
		t.Fatalf("user-agent was not escaped")
	}
	if !strings.Contains(out, "Your password was changed") {
		t.Fatalf("missing heading copy")
	}
	if !strings.HasPrefix(out, "<!DOCTYPE html>") {
		t.Fatalf("expected a full HTML document")
	}
	if !strings.Contains(out, "1.2.3.4") {
		t.Fatalf("expected the request IP in the meta block")
	}
}

func TestNewLoginHTML_EscapesAndRenders(t *testing.T) {
	out := NewLoginHTML(`"><img src=x onerror=alert(1)>`, "", "", "")
	if strings.Contains(out, "<img src=x") {
		t.Fatalf("display name was not escaped")
	}
	if !strings.Contains(out, "New sign-in detected") {
		t.Fatalf("missing heading copy")
	}
	// Empty meta fields render as "unknown".
	if !strings.Contains(out, "unknown") {
		t.Fatalf("empty meta fields should render as 'unknown'")
	}
}

func TestSecuritySubjectsStable(t *testing.T) {
	if PasswordChangedSubject == "" || NewLoginSubject == "" {
		t.Fatalf("security subjects must be non-empty")
	}
}
