package auth

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"errors"
	"fmt"
	"strings"
	"unicode"

	"golang.org/x/crypto/argon2"
	"golang.org/x/crypto/bcrypt"
)

// Password hashing for the platform.
//
// New and changed passwords are hashed with Argon2id (the algorithm
// the security checklist mandates and OWASP recommends for password
// storage). Existing accounts created before this migration carry a
// bcrypt hash; VerifyPassword detects the scheme from the stored
// string and validates either, so no user is forced to reset. The
// login path calls NeedsRehash and, on a successful bcrypt (or
// weak-parameter Argon2id) verify, transparently re-hashes the
// plaintext with current Argon2id parameters and persists it -- a
// silent, zero-touch upgrade.
//
// Argon2id parameters (RFC 9106 / OWASP "second" configuration,
// tuned for an interactive login on a server-class host):
//
//   memory      = 64 MiB
//   iterations  = 3
//   parallelism = 2
//   salt        = 16 bytes (crypto/rand)
//   key         = 32 bytes
//
// These are encoded into the PHC string so a later parameter bump is
// detected by NeedsRehash and upgraded on next login without a schema
// change. The verifier reads the parameters from the stored hash, so
// raising the constants below never breaks verification of older
// Argon2id hashes.

const (
	argon2idMemoryKiB  uint32 = 64 * 1024 // 64 MiB
	argon2idTime       uint32 = 3
	argon2idThreads    uint8  = 2
	argon2idSaltLength uint32 = 16
	argon2idKeyLength  uint32 = 32

	// argon2idVersion mirrors argon2.Version (0x13 = 19). Kept as a
	// named constant so the PHC string and the parse guard agree.
	argon2idVersion = argon2.Version
)

// ErrPasswordMismatch is returned by VerifyPassword when the plaintext
// does not match the stored hash. Callers MUST treat this and an
// "unparseable hash" error identically in user-facing responses so the
// failure mode is not an oracle.
var ErrPasswordMismatch = errors.New("password does not match")

// HashPassword hashes a plaintext password with Argon2id and returns
// the standard PHC-format string:
//
//	$argon2id$v=19$m=65536,t=3,p=2$<b64 salt>$<b64 hash>
//
// The caller is responsible for length/complexity validation
// (ValidatePasswordComplexity); HashPassword only enforces the
// hard upper bound to avoid hashing an unbounded blob.
func HashPassword(plaintext string) (string, error) {
	if len(plaintext) == 0 {
		return "", fmt.Errorf("password must not be empty")
	}
	if len(plaintext) > PasswordMaxLength {
		return "", fmt.Errorf("password must be at most %d characters", PasswordMaxLength)
	}

	salt := make([]byte, argon2idSaltLength)
	if _, err := rand.Read(salt); err != nil {
		return "", fmt.Errorf("generate salt: %w", err)
	}

	key := argon2.IDKey(
		[]byte(plaintext), salt,
		argon2idTime, argon2idMemoryKiB, argon2idThreads, argon2idKeyLength,
	)

	return fmt.Sprintf(
		"$argon2id$v=%d$m=%d,t=%d,p=%d$%s$%s",
		argon2idVersion,
		argon2idMemoryKiB, argon2idTime, argon2idThreads,
		base64.RawStdEncoding.EncodeToString(salt),
		base64.RawStdEncoding.EncodeToString(key),
	), nil
}

// VerifyPassword checks plaintext against a stored hash, transparently
// supporting both Argon2id (PHC string) and legacy bcrypt hashes.
// Returns nil on match, ErrPasswordMismatch on a clean mismatch, or a
// wrapped error when the stored hash is malformed/unsupported.
func VerifyPassword(stored, plaintext string) error {
	switch {
	case strings.HasPrefix(stored, "$argon2id$"):
		return verifyArgon2id(stored, plaintext)
	case strings.HasPrefix(stored, "$2a$"),
		strings.HasPrefix(stored, "$2b$"),
		strings.HasPrefix(stored, "$2y$"):
		if err := bcrypt.CompareHashAndPassword([]byte(stored), []byte(plaintext)); err != nil {
			if errors.Is(err, bcrypt.ErrMismatchedHashAndPassword) {
				return ErrPasswordMismatch
			}
			return fmt.Errorf("bcrypt verify: %w", err)
		}
		return nil
	default:
		return fmt.Errorf("unsupported password hash format")
	}
}

// NeedsRehash reports whether a stored hash should be upgraded to the
// current Argon2id parameters on the next successful verify. True for:
//   - any bcrypt hash (legacy scheme), or
//   - an Argon2id hash whose memory/time/threads are weaker than the
//     current policy constants.
// Returns false for an unparseable hash (the login path will have
// already failed verification, so there is nothing to upgrade).
func NeedsRehash(stored string) bool {
	if !strings.HasPrefix(stored, "$argon2id$") {
		// bcrypt or any non-Argon2id scheme -> upgrade.
		return true
	}
	mem, time, threads, _, _, err := parseArgon2id(stored)
	if err != nil {
		return false
	}
	return mem < argon2idMemoryKiB || time < argon2idTime || threads < argon2idThreads
}

// verifyArgon2id validates plaintext against an Argon2id PHC string in
// constant time with respect to the derived key.
func verifyArgon2id(stored, plaintext string) error {
	mem, time, threads, salt, want, err := parseArgon2id(stored)
	if err != nil {
		return err
	}
	got := argon2.IDKey([]byte(plaintext), salt, time, mem, threads, uint32(len(want)))
	if subtle.ConstantTimeCompare(got, want) == 1 {
		return nil
	}
	return ErrPasswordMismatch
}

// parseArgon2id decodes an Argon2id PHC string into its parameters,
// salt, and key. Rejects any other algorithm or version.
func parseArgon2id(stored string) (mem, time uint32, threads uint8, salt, key []byte, err error) {
	// Format: $argon2id$v=19$m=65536,t=3,p=2$<salt>$<key>
	parts := strings.Split(stored, "$")
	if len(parts) != 6 || parts[0] != "" || parts[1] != "argon2id" {
		return 0, 0, 0, nil, nil, fmt.Errorf("invalid argon2id hash format")
	}

	var version int
	if _, err = fmt.Sscanf(parts[2], "v=%d", &version); err != nil {
		return 0, 0, 0, nil, nil, fmt.Errorf("invalid argon2id version field: %w", err)
	}
	if version != argon2idVersion {
		return 0, 0, 0, nil, nil, fmt.Errorf("unsupported argon2id version %d", version)
	}

	var p int
	if _, err = fmt.Sscanf(parts[3], "m=%d,t=%d,p=%d", &mem, &time, &p); err != nil {
		return 0, 0, 0, nil, nil, fmt.Errorf("invalid argon2id params: %w", err)
	}
	if p < 1 || p > 255 {
		return 0, 0, 0, nil, nil, fmt.Errorf("invalid argon2id parallelism %d", p)
	}
	threads = uint8(p)

	salt, err = base64.RawStdEncoding.DecodeString(parts[4])
	if err != nil {
		return 0, 0, 0, nil, nil, fmt.Errorf("decode argon2id salt: %w", err)
	}
	key, err = base64.RawStdEncoding.DecodeString(parts[5])
	if err != nil {
		return 0, 0, 0, nil, nil, fmt.Errorf("decode argon2id key: %w", err)
	}
	if len(salt) == 0 || len(key) == 0 {
		return 0, 0, 0, nil, nil, fmt.Errorf("empty argon2id salt or key")
	}
	return mem, time, threads, salt, key, nil
}

// ---------------------------------------------------------------------------
// Strong random password generation
// ---------------------------------------------------------------------------

const (
	_pwLower   = "abcdefghijkmnpqrstuvwxyz"   // no l/o (confusable)
	_pwUpper   = "ABCDEFGHJKLMNPQRSTUVWXYZ"   // no I/O
	_pwDigit   = "23456789"                   // no 0/1
	_pwSymbol  = "!@#$%^&*()-_=+[]{}"
	_pwAll     = _pwLower + _pwUpper + _pwDigit + _pwSymbol
)

// GenerateStrongPassword returns a cryptographically random password of
// length n (clamped to a minimum of 16) that is guaranteed to contain
// at least one lowercase, uppercase, digit, and symbol -- i.e. it
// satisfies ValidatePasswordComplexity by construction. Used for the
// admin-seed fallback when AUTH_ADMIN_PASSWORD is not configured.
func GenerateStrongPassword(n int) (string, error) {
	if n < 16 {
		n = 16
	}
	if n > PasswordMaxLength {
		n = PasswordMaxLength
	}

	out := make([]byte, 0, n)
	// Guarantee one of each class first.
	for _, set := range []string{_pwLower, _pwUpper, _pwDigit, _pwSymbol} {
		c, err := randChar(set)
		if err != nil {
			return "", err
		}
		out = append(out, c)
	}
	// Fill the remainder from the full alphabet.
	for len(out) < n {
		c, err := randChar(_pwAll)
		if err != nil {
			return "", err
		}
		out = append(out, c)
	}
	// Fisher-Yates shuffle so the guaranteed-class characters are not
	// pinned to the first four positions.
	for i := len(out) - 1; i > 0; i-- {
		j, err := randInt(i + 1)
		if err != nil {
			return "", err
		}
		out[i], out[j] = out[j], out[i]
	}
	return string(out), nil
}

// randChar returns a uniformly random byte from set using crypto/rand.
func randChar(set string) (byte, error) {
	idx, err := randInt(len(set))
	if err != nil {
		return 0, err
	}
	return set[idx], nil
}

// randInt returns a uniformly random int in [0, max) using crypto/rand
// with rejection sampling to avoid modulo bias.
func randInt(max int) (int, error) {
	if max <= 0 {
		return 0, fmt.Errorf("randInt: max must be positive")
	}
	// 256 mod max gives the number of values that would bias; reject
	// any byte in the top biased range.
	limit := 256 - (256 % max)
	buf := make([]byte, 1)
	for {
		if _, err := rand.Read(buf); err != nil {
			return 0, fmt.Errorf("randInt: read random: %w", err)
		}
		if int(buf[0]) < limit {
			return int(buf[0]) % max, nil
		}
	}
}

// ---------------------------------------------------------------------------
// Complexity policy
// ---------------------------------------------------------------------------

// PasswordComplexityMinClasses is the number of distinct character
// classes (lowercase, uppercase, digit, symbol) a password must mix.
const PasswordComplexityMinClasses = 3

// commonPasswords is a small, high-signal denylist of the most-abused
// passwords. It is intentionally compact (not a multi-million entry
// list): online breach detection (HaveIBeenPwned, added separately) is
// the comprehensive control; this catches the trivially weak inputs
// before they ever reach the breach API.
var commonPasswords = map[string]struct{}{
	"password": {}, "password1": {}, "password123": {}, "123456": {},
	"123456789": {}, "12345678": {}, "qwerty": {}, "qwerty123": {},
	"111111": {}, "000000": {}, "iloveyou": {}, "admin": {},
	"admin123": {}, "welcome": {}, "welcome1": {}, "letmein": {},
	"monkey": {}, "dragon": {}, "abc123": {}, "changeme": {},
	"passw0rd": {}, "p@ssw0rd": {}, "trustno1": {}, "sunshine": {},
}

// ValidatePasswordComplexity enforces the platform password policy:
//   - length within [PasswordMinLength, PasswordMaxLength];
//   - at least PasswordComplexityMinClasses of the four character
//     classes (lower, upper, digit, symbol);
//   - not in the common-password denylist;
//   - does not contain (case-insensitive) the username or the local
//     part of the email, which are trivially guessable.
//
// username and email may be empty (e.g. an admin-set password where
// only the new value is known); the substring checks are skipped for
// any empty identity field.
func ValidatePasswordComplexity(plaintext, username, email string) error {
	if len(plaintext) < PasswordMinLength {
		return fmt.Errorf("password must be at least %d characters", PasswordMinLength)
	}
	if len(plaintext) > PasswordMaxLength {
		return fmt.Errorf("password must be at most %d characters", PasswordMaxLength)
	}

	var hasLower, hasUpper, hasDigit, hasSymbol bool
	for _, r := range plaintext {
		switch {
		case unicode.IsLower(r):
			hasLower = true
		case unicode.IsUpper(r):
			hasUpper = true
		case unicode.IsDigit(r):
			hasDigit = true
		default:
			hasSymbol = true
		}
	}
	classes := 0
	for _, ok := range []bool{hasLower, hasUpper, hasDigit, hasSymbol} {
		if ok {
			classes++
		}
	}
	if classes < PasswordComplexityMinClasses {
		return fmt.Errorf(
			"password must contain at least %d of: lowercase, uppercase, digit, symbol",
			PasswordComplexityMinClasses,
		)
	}

	lower := strings.ToLower(plaintext)
	if _, bad := commonPasswords[lower]; bad {
		return fmt.Errorf("password is too common; choose a less predictable password")
	}

	if u := strings.ToLower(strings.TrimSpace(username)); u != "" && strings.Contains(lower, u) {
		return fmt.Errorf("password must not contain your username")
	}
	if e := strings.ToLower(strings.TrimSpace(email)); e != "" {
		local := e
		if at := strings.IndexByte(e, '@'); at > 0 {
			local = e[:at]
		}
		if local != "" && len(local) >= 3 && strings.Contains(lower, local) {
			return fmt.Errorf("password must not contain your email address")
		}
	}

	return nil
}
