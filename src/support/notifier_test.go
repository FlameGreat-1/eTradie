package support

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/rs/zerolog"
)

// ---------------------------------------------------------------------------
// discordEscape
// ---------------------------------------------------------------------------

func TestDiscordEscape_MarkdownAndMentions(t *testing.T) {
	in := "Hello `code` *bold* _italic_ ~strike~ |spoiler| @everyone @here @role contact"
	got := discordEscape(in)
	for _, raw := range []string{"`code`", "*bold*", "_italic_", "~strike~", "|spoiler|"} {
		if strings.Contains(got, raw) {
			t.Fatalf("discordEscape failed to escape %q: %q", raw, got)
		}
	}
	// Every '@' MUST be followed by U+200B so the Discord mention
	// parser cannot match @everyone / @here / @role.
	for _, mention := range []string{"@everyone", "@here", "@role"} {
		if strings.Contains(got, mention) {
			t.Fatalf("discordEscape failed to defang %q: %q", mention, got)
		}
	}
	if strings.Count(got, "\u200b") < 3 {
		t.Fatalf("want >=3 ZWSP insertions (one per '@'), got %d in %q", strings.Count(got, "\u200b"), got)
	}
}

// ---------------------------------------------------------------------------
// postWithRetry: retry policy
// ---------------------------------------------------------------------------

func newRecordingNotifier(t *testing.T) *Notifier {
	t.Helper()
	return NewNotifier(&Config{}, nil, zerolog.Nop())
}

func TestPostWithRetry_SucceedsOnFirstAttempt(t *testing.T) {
	var hits int64
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt64(&hits, 1)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	n := newRecordingNotifier(t)
	n.postWithRetry(context.Background(), "unit", srv.URL, "application/json", []byte(`{}`), nil)

	if got := atomic.LoadInt64(&hits); got != 1 {
		t.Fatalf("want exactly 1 hit, got %d", got)
	}
}

func TestPostWithRetry_RetriesOn5xxThenGivesUp(t *testing.T) {
	var hits int64
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt64(&hits, 1)
		http.Error(w, "down", http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	n := newRecordingNotifier(t)
	n.postWithRetry(context.Background(), "unit", srv.URL, "application/json", []byte(`{}`), nil)

	// Retry budget = notifierMaxRetries + 1 attempts.
	want := int64(notifierMaxRetries + 1)
	if got := atomic.LoadInt64(&hits); got != want {
		t.Fatalf("want %d hits after 5xx retries, got %d", want, got)
	}
}

func TestPostWithRetry_4xxShortCircuits(t *testing.T) {
	var hits int64
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt64(&hits, 1)
		http.Error(w, "nope", http.StatusBadRequest)
	}))
	defer srv.Close()

	n := newRecordingNotifier(t)
	n.postWithRetry(context.Background(), "unit", srv.URL, "application/json", []byte(`{}`), nil)

	if got := atomic.LoadInt64(&hits); got != 1 {
		t.Fatalf("want 1 hit on 4xx (non-recoverable), got %d", got)
	}
}

func TestPostWithRetry_429IsRecoverable(t *testing.T) {
	var hits int64
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		curr := atomic.AddInt64(&hits, 1)
		if curr < 2 {
			http.Error(w, "slow down", http.StatusTooManyRequests)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	n := newRecordingNotifier(t)
	// Backoff factor is 2s * 2^(attempt-1); 1 retry = 2s. Bound the
	// wait so a flaky CI host that briefly hangs the request does
	// not stretch the test arbitrarily.
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	n.postWithRetry(ctx, "unit", srv.URL, "application/json", []byte(`{}`), nil)

	if got := atomic.LoadInt64(&hits); got < 2 {
		t.Fatalf("want >=2 hits for 429 retry, got %d", got)
	}
}

func TestPostWithRetry_RespectsCancelledContext(t *testing.T) {
	var hits int64
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt64(&hits, 1)
		http.Error(w, "down", http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	n := newRecordingNotifier(t)
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // pre-cancelled

	n.postWithRetry(ctx, "unit", srv.URL, "application/json", []byte(`{}`), nil)

	// First attempt is permitted because the loop checks the
	// context only between attempts. So we expect exactly one hit
	// even though the context is dead.
	if got := atomic.LoadInt64(&hits); got != 1 {
		t.Fatalf("want 1 hit when ctx pre-cancelled, got %d", got)
	}
}

// ---------------------------------------------------------------------------
// Track / TrackDone / Shutdown
// ---------------------------------------------------------------------------

func TestNotifier_ShutdownDrainsTrackedWork(t *testing.T) {
	n := newRecordingNotifier(t)

	var started, finished sync.WaitGroup
	started.Add(1)
	finished.Add(1)

	n.Track()
	go func() {
		defer n.TrackDone()
		defer finished.Done()
		started.Done()
		time.Sleep(80 * time.Millisecond)
	}()

	// Wait for the goroutine to register itself.
	started.Wait()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := n.Shutdown(ctx); err != nil {
		t.Fatalf("Shutdown returned %v", err)
	}

	// The goroutine must have finished by now.
	done := make(chan struct{})
	go func() {
		finished.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(50 * time.Millisecond):
		t.Fatal("tracked goroutine did not finish before Shutdown returned")
	}
}

func TestNotifier_ShutdownRespectsDeadline(t *testing.T) {
	n := newRecordingNotifier(t)

	n.Track()
	go func() {
		defer n.TrackDone()
		time.Sleep(500 * time.Millisecond)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	err := n.Shutdown(ctx)
	if err == nil {
		t.Fatal("want ctx err when Shutdown deadline expires, got nil")
	}
}

// ---------------------------------------------------------------------------
// sendDiscord: escape user-controlled subject
// ---------------------------------------------------------------------------

func TestSendDiscord_EscapesSubject(t *testing.T) {
	var gotBody string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		buf := make([]byte, 4096)
		nRead, _ := r.Body.Read(buf)
		gotBody = string(buf[:nRead])
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	n := NewNotifier(&Config{DiscordWebhookURL: srv.URL}, nil, zerolog.Nop())
	ev := Event{
		Kind: EventNewTicket,
		Ticket: &Ticket{
			ID:        "a",
			PublicRef: "TKT-FFFF",
			Email:     "a@b.co",
			Subject:   "@everyone urgent issue",
			Category:  CategoryGeneral,
			Priority:  PriorityHigh,
			Status:    StatusOpen,
			Channel:   ChannelContact,
			Messages:  []Message{{Body: "body"}},
		},
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	n.sendDiscord(ctx, ev)

	if strings.Contains(gotBody, "@everyone") {
		t.Fatalf("discord payload leaked unescaped @everyone: %q", gotBody)
	}
	if !strings.Contains(gotBody, "TKT-FFFF") {
		t.Fatalf("discord payload missing public_ref: %q", gotBody)
	}
}
