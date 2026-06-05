package auth

import (
	"fmt"
	"strings"
	"testing"

	"golang.org/x/crypto/bcrypt"
)

func TestHashPassword_ProducesParseablePHCAndIsSalted(t *testing.T) {
	const pw = "Str0ng-P@ssphrase!"
	h1, err := HashPassword(pw)
	if err != nil {
		t.Fatalf("HashPassword: %v", err)
	}
	if !strings.HasPrefix(h1, "$argon2id$") {
		t.Fatalf("expected argon2id PHC prefix, got %q", h1)
	}
	expectParams := fmt.Sprintf("m=%d,t=%d,p=%d", argon2idMemoryKiB, argon2idTime, argon2idThreads)
	if !strings.Contains(h1, expectParams) {
		t.Fatalf("hash %q missing current params %q", h1, expectParams)
	}
	h2, err := HashPassword(pw)
	if err != nil {
		t.Fatalf("HashPassword (2): %v", err)
	}
	if h1 == h2 {
		t.Fatalf("two hashes of the same password are identical; salt not random")
	}
}

func TestVerifyPassword_Argon2idMatchAndMismatch(t *testing.T) {
	const pw = "Str0ng-P@ssphrase!"
	h, err := HashPassword(pw)
	if err != nil {
		t.Fatalf("HashPassword: %v", err)
	}
	if err := VerifyPassword(h, pw); err != nil {
		t.Fatalf("VerifyPassword should accept the correct password: %v", err)
	}
	if err := VerifyPassword(h, pw+"x"); err != ErrPasswordMismatch {
		t.Fatalf("expected ErrPasswordMismatch, got %v", err)
	}
}

func TestVerifyPassword_LegacyBcryptStillVerifies(t *testing.T) {
	const pw = "Str0ng-P@ssphrase!"
	legacy, err := bcrypt.GenerateFromPassword([]byte(pw), bcrypt.DefaultCost)
	if err != nil {
		t.Fatalf("bcrypt seed: %v", err)
	}
	if err := VerifyPassword(string(legacy), pw); err != nil {
		t.Fatalf("legacy bcrypt hash must still verify (no forced reset): %v", err)
	}
	if err := VerifyPassword(string(legacy), "wrong"); err != ErrPasswordMismatch {
		t.Fatalf("expected ErrPasswordMismatch for bad bcrypt password, got %v", err)
	}
}

func TestVerifyPassword_UnsupportedFormat(t *testing.T) {
	if err := VerifyPassword("not-a-hash", "x"); err == nil {
		t.Fatalf("expected error for unsupported hash format")
	}
}

func TestNeedsRehash(t *testing.T) {
	const pw = "Str0ng-P@ssphrase!"

	bc, _ := bcrypt.GenerateFromPassword([]byte(pw), bcrypt.DefaultCost)
	if !NeedsRehash(string(bc)) {
		t.Fatalf("bcrypt hash should need rehash")
	}

	current, _ := HashPassword(pw)
	if NeedsRehash(current) {
		t.Fatalf("current-param argon2id hash should NOT need rehash")
	}

	// Deliberately weak-param argon2id hash (m below policy).
	weak := fmt.Sprintf("$argon2id$v=%d$m=%d,t=%d,p=%d$c2FsdHNhbHQ$a2V5a2V5a2V5a2V5",
		argon2idVersion, argon2idMemoryKiB/2, argon2idTime, argon2idThreads)
	if !NeedsRehash(weak) {
		t.Fatalf("weaker-param argon2id hash should need rehash")
	}
}

func TestValidatePasswordComplexity(t *testing.T) {
	tests := []struct {
		name     string
		pw       string
		user     string
		email    string
		wantErr  bool
	}{
		{"valid", "Str0ng-P@ss!", "alice", "alice@example.com", false},
		{"too short", "Ab1!", "", "", true},
		{"two classes only", "abcdefghij", "", "", true},
		{"common password", "password123", "", "", true},
		{"contains username", "alice-Str0ng!", "alice", "", true},
		{"contains email local", "bobby-Str0ng1!", "", "bobby@example.com", true},
		{"three classes ok", "Abcdef123", "", "", false},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidatePasswordComplexity(tc.pw, tc.user, tc.email)
			if tc.wantErr && err == nil {
				t.Fatalf("expected error for %q", tc.pw)
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error for %q: %v", tc.pw, err)
			}
		})
	}
}

func TestGenerateStrongPassword(t *testing.T) {
	p, err := GenerateStrongPassword(8) // below the clamp
	if err != nil {
		t.Fatalf("GenerateStrongPassword: %v", err)
	}
	if len(p) < 16 {
		t.Fatalf("length should be clamped to >=16, got %d", len(p))
	}
	// Satisfies complexity by construction.
	if err := ValidatePasswordComplexity(p, "", ""); err != nil {
		t.Fatalf("generated password failed complexity: %v", err)
	}
	// Two generations differ.
	q, _ := GenerateStrongPassword(20)
	if p == q {
		t.Fatalf("two generated passwords are identical")
	}
}
