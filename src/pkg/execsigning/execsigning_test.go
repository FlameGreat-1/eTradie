package execsigning

import (
	"testing"
	"time"
)

func baseFields() Fields {
	return Fields{
		Timestamp:  time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC),
		Nonce:      "analysis-123",
		UserID:     "user-abc",
		Symbol:     "EURUSD",
		Direction:  "LONG",
		AnalysisID: "analysis-123",
	}
}

func TestCanonicalDeterministic(t *testing.T) {
	f := baseFields()
	if f.Canonical() != f.Canonical() {
		t.Fatal("canonical is not deterministic")
	}
	// Same logical fields built separately must match.
	g := baseFields()
	if f.Canonical() != g.Canonical() {
		t.Fatal("identical fields produced different canonical strings")
	}
}

func TestCanonicalFieldSensitivity(t *testing.T) {
	base := baseFields()
	mutators := map[string]func(*Fields){
		"timestamp":  func(f *Fields) { f.Timestamp = f.Timestamp.Add(time.Second) },
		"nonce":      func(f *Fields) { f.Nonce = "other" },
		"user_id":    func(f *Fields) { f.UserID = "other" },
		"symbol":     func(f *Fields) { f.Symbol = "GBPUSD" },
		"direction":  func(f *Fields) { f.Direction = "SHORT" },
		"analysis":   func(f *Fields) { f.AnalysisID = "other" },
	}
	baseHash := base.CanonicalHash()
	for name, m := range mutators {
		f := baseFields()
		m(&f)
		if f.CanonicalHash() == baseHash {
			t.Errorf("changing %s did not change the canonical hash", name)
		}
	}
}

func TestSignVerifyRoundTrip(t *testing.T) {
	key := []byte("this-is-a-32-byte-minimum-hmac-key!!")
	f := baseFields()
	sig := Sign(key, f)
	if !Verify(key, f, sig) {
		t.Fatal("valid signature failed to verify")
	}
}

func TestVerifyRejectsWrongKey(t *testing.T) {
	f := baseFields()
	sig := Sign([]byte("key-one-key-one-key-one-key-one-aa"), f)
	if Verify([]byte("key-two-key-two-key-two-key-two-bb"), f, sig) {
		t.Fatal("signature verified under the wrong key")
	}
}

func TestVerifyRejectsTamperedField(t *testing.T) {
	key := []byte("this-is-a-32-byte-minimum-hmac-key!!")
	f := baseFields()
	sig := Sign(key, f)
	f.Symbol = "GBPUSD" // tamper after signing
	if Verify(key, f, sig) {
		t.Fatal("signature verified after a field was tampered")
	}
}

func TestVerifyRejectsMalformedHex(t *testing.T) {
	key := []byte("this-is-a-32-byte-minimum-hmac-key!!")
	f := baseFields()
	if Verify(key, f, "not-hex-zzzz") {
		t.Fatal("malformed hex signature verified")
	}
}
