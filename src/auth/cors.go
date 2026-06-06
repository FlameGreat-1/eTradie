package auth

import (
	"net/url"
	"strings"
)

// BuildCORSAllowlist normalises and validates a credentialed-CORS
// origin allow-list. It is the single source of truth for origin
// validation across every Go service (gateway, execution, management).
//
// An entry is ACCEPTED only when it is a full origin: scheme + host +
// optional port, with no path, query, or fragment. The returned map is
// keyed by the normalised "scheme://host" form for O(1) lookup in the
// CORS middleware.
//
// An entry is REJECTED (returned in the second slice, never added to
// the map) when it is:
//   - "*"            : the wildcard is forbidden under credentialed CORS;
//   - "null"         : the literal null origin (sandboxed iframes,
//                      data: URLs) is never a legitimate allow-list entry;
//   - empty / whitespace-only;
//   - not parseable by url.Parse;
//   - not http or https scheme;
//   - missing a host;
//   - carrying a path, query, or fragment.
//
// Callers decide the failure posture: the gateway converts a non-empty
// rejected slice into a startup error (fail the deploy); execution and
// management log the rejected entries and serve only the accepted ones
// (fail safe — a bad origin is dropped, never reflected).
func BuildCORSAllowlist(raw []string) (allowed map[string]bool, rejected []string) {
	allowed = make(map[string]bool, len(raw))
	for _, entry := range raw {
		s := strings.TrimSpace(entry)
		if s == "" {
			// Empty entries are ignored, not reported: they are the
			// benign result of a trailing comma in the env var.
			continue
		}
		if s == "*" || strings.EqualFold(s, "null") {
			rejected = append(rejected, s)
			continue
		}
		u, err := url.Parse(s)
		if err != nil {
			rejected = append(rejected, s)
			continue
		}
		if u.Scheme != "http" && u.Scheme != "https" {
			rejected = append(rejected, s)
			continue
		}
		if u.Host == "" {
			rejected = append(rejected, s)
			continue
		}
		if u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
			rejected = append(rejected, s)
			continue
		}
		allowed[u.Scheme+"://"+u.Host] = true
	}
	return allowed, rejected
}
