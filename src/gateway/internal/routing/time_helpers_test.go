package routing

import "time"

// timeNowUTC is a tiny shim used by tests that need the current UTC
// hour. Kept in its own file so future time-injection refactors (e.g.
// a Clock interface) can replace just this helper without touching
// every test.
func timeNowUTC() time.Time { return time.Now().UTC() }
