package support

import (
	"strings"
	"testing"
)

func TestValidateEmail(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		want    string
		wantErr bool
	}{
		{"plain", "User@Example.com", "user@example.com", false},
		{"trim", "  user@example.com  ", "user@example.com", false},
		{"missing-at", "user.example.com", "", true},
		{"missing-dot-after-at", "user@example", "", true},
		{"empty", "", "", true},
		{"trailing-at", "user@", "", true},
		{"leading-at", "@example.com", "", true},
		{"whitespace-inside", "us er@example.com", "", true},
		{"newline-inside", "user@example.com\n", "", true},
		{"too-long", strings.Repeat("a", MaxEmailLen) + "@x.co", "", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := ValidateEmail(tc.in)
			if (err != nil) != tc.wantErr {
				t.Fatalf("ValidateEmail(%q) err=%v wantErr=%v", tc.in, err, tc.wantErr)
			}
			if got != tc.want {
				t.Fatalf("ValidateEmail(%q)=%q want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestValidateName(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		wantErr bool
	}{
		{"empty-ok", "", false},
		{"normal", "Jane Doe", false},
		{"tab-ok", "Jane\tDoe", false},
		{"control-rejected", "Jane\x01Doe", true},
		{"too-long", strings.Repeat("a", MaxNameLen+1), true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := ValidateName(tc.in)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err=%v wantErr=%v", err, tc.wantErr)
			}
		})
	}
}

func TestValidateSubject(t *testing.T) {
	if _, err := ValidateSubject("  ok  "); err != nil {
		t.Fatalf("want nil for ' ok ', got %v", err)
	}
	if _, err := ValidateSubject("  ab  "); err == nil {
		t.Fatal("want err for sub-min, got nil")
	}
	if _, err := ValidateSubject(strings.Repeat("a", MaxSubjectLen+1)); err == nil {
		t.Fatal("want err for over-max, got nil")
	}
}

func TestValidateBody(t *testing.T) {
	if _, err := ValidateBody("hello"); err != nil {
		t.Fatalf("want nil for 'hello' (5 chars), got %v", err)
	}
	if _, err := ValidateBody("abcd"); err == nil {
		t.Fatal("want err for 4-char body")
	}
	if _, err := ValidateBody(strings.Repeat("a", MaxBodyLen+1)); err == nil {
		t.Fatal("want err for over-max body")
	}
}

func TestNormaliseCategory(t *testing.T) {
	if c, err := NormaliseCategory(""); err != nil || c != CategoryGeneral {
		t.Fatalf("empty -> %v / %v", c, err)
	}
	if c, err := NormaliseCategory("  Billing  "); err != nil || c != CategoryBilling {
		t.Fatalf("billing -> %v / %v", c, err)
	}
	if _, err := NormaliseCategory("unknown"); err == nil {
		t.Fatal("want err for unknown")
	}
}

func TestNormalisePriority(t *testing.T) {
	if p, err := NormalisePriority(""); err != nil || p != PriorityNormal {
		t.Fatalf("empty -> %v / %v", p, err)
	}
	if p, err := NormalisePriority("URGENT"); err != nil || p != PriorityUrgent {
		t.Fatalf("urgent -> %v / %v", p, err)
	}
	if _, err := NormalisePriority("insane"); err == nil {
		t.Fatal("want err for unknown")
	}
}

func TestTruncateUserAgent(t *testing.T) {
	long := strings.Repeat("x", MaxUserAgentLen+50)
	got := TruncateUserAgent(long)
	if len(got) != MaxUserAgentLen {
		t.Fatalf("len=%d want %d", len(got), MaxUserAgentLen)
	}
	short := "Mozilla/5.0"
	if TruncateUserAgent(short) != short {
		t.Fatalf("short string mutated")
	}
}

func TestEnumIsValid(t *testing.T) {
	for _, s := range []TicketStatus{StatusOpen, StatusPending, StatusResolved, StatusClosed} {
		if !s.IsValid() {
			t.Fatalf("status %q should be valid", s)
		}
	}
	if TicketStatus("weird").IsValid() {
		t.Fatal("unexpected valid status")
	}
	for _, p := range []TicketPriority{PriorityLow, PriorityNormal, PriorityHigh, PriorityUrgent} {
		if !p.IsValid() {
			t.Fatalf("priority %q should be valid", p)
		}
	}
	if TicketPriority("weird").IsValid() {
		t.Fatal("unexpected valid priority")
	}
	for _, c := range []TicketCategory{
		CategoryGeneral, CategoryBilling, CategoryTechnical,
		CategoryAccount, CategoryFeedback, CategoryBug,
		CategoryFeature, CategorySecurity, CategoryComplaint,
	} {
		if !c.IsValid() {
			t.Fatalf("category %q should be valid", c)
		}
	}
	if TicketCategory("weird").IsValid() {
		t.Fatal("unexpected valid category")
	}
	for _, ch := range []TicketChannel{ChannelWeb, ChannelContact, ChannelEmail} {
		if !ch.IsValid() {
			t.Fatalf("channel %q should be valid", ch)
		}
	}
	if TicketChannel("weird").IsValid() {
		t.Fatal("unexpected valid channel")
	}
	for _, a := range []MessageAuthorKind{AuthorKindUser, AuthorKindStaff, AuthorKindSystem} {
		if !a.IsValid() {
			t.Fatalf("author %q should be valid", a)
		}
	}
	for _, a := range []TicketAction{
		ActionCreated, ActionReplied, ActionClosed,
		ActionReopened, ActionHoneypotDropped,
	} {
		if !a.IsValid() {
			t.Fatalf("action %q should be valid", a)
		}
	}
	if TicketAction("weird").IsValid() {
		t.Fatal("unexpected valid action")
	}
	for _, k := range []AuditActorKind{ActorUser, ActorStaff, ActorSystem, ActorAnonymous} {
		if !k.IsValid() {
			t.Fatalf("actor_kind %q should be valid", k)
		}
	}
	if AuditActorKind("weird").IsValid() {
		t.Fatal("unexpected valid actor_kind")
	}
}

func TestGenerateID_FormatAndUniqueness(t *testing.T) {
	seen := make(map[string]bool, 256)
	for i := 0; i < 256; i++ {
		id := generateID()
		if len(id) != 32 {
			t.Fatalf("id len=%d want 32", len(id))
		}
		for _, r := range id {
			if !((r >= '0' && r <= '9') || (r >= 'a' && r <= 'f')) {
				t.Fatalf("non-hex char %q in id %q", r, id)
			}
		}
		if seen[id] {
			t.Fatalf("duplicate id %q at iter %d", id, i)
		}
		seen[id] = true
	}
}

func TestGeneratePublicRef_Format(t *testing.T) {
	for i := 0; i < 64; i++ {
		ref := generatePublicRef()
		if !strings.HasPrefix(ref, "TKT-") {
			t.Fatalf("ref %q missing TKT- prefix", ref)
		}
		rest := strings.TrimPrefix(ref, "TKT-")
		if len(rest) != 8 {
			t.Fatalf("ref body %q len=%d want 8", rest, len(rest))
		}
		for _, r := range rest {
			if !((r >= '0' && r <= '9') || (r >= 'A' && r <= 'F')) {
				t.Fatalf("non-uppercase-hex char %q in ref %q", r, ref)
			}
		}
	}
}
