package auth

import (
	"net"
	"net/http"
	"strings"
	"sync"
)

// ---------------------------------------------------------------------------
// Trust-aware client-IP resolver
//
// Determines the real client IP behind a layered proxy chain such as
// Cloudflare -> edge-ingress -> envoy -> gateway. The previous
// implementation in handlers.go (clientIP) trusted X-Forwarded-For and
// X-Real-IP from any peer, which let an attacker who reached the origin
// IP directly spoof those headers and defeat per-IP rate limits.
//
// The resolver only honours forwarding headers when the immediate TCP
// peer is in the configured trusted-proxy set. When the peer is not
// trusted, forwarding headers are ignored entirely and the peer address
// is returned, which makes header spoofing impossible from outside the
// trusted edge.
// ---------------------------------------------------------------------------

// Header names honoured by the resolver. Lower-case is canonical for
// http.Header access (Go normalises to MIME case internally, but using
// canonical-case strings here keeps grep-ability with envoy/edge logs).
const (
	headerCFConnectingIP = "CF-Connecting-IP"
	headerXForwardedFor  = "X-Forwarded-For"
	headerXRealIP        = "X-Real-IP"
)

// ClientIPResolver resolves the real client IP for an http.Request.
//
// Concurrent use is safe: trustedNets is immutable after New().
type ClientIPResolver struct {
	trustedNets []*net.IPNet
}

// NewClientIPResolver builds a resolver from a list of CIDRs.
//
// Each CIDR is parsed once at construction time; invalid entries are
// skipped (they are reported by ParseTrustedCIDRs which the caller
// uses for validation). When trustWellKnownCloudflare is true, the
// resolver additionally trusts the published Cloudflare IPv4 and
// IPv6 ranges as if they had been listed explicitly.
func NewClientIPResolver(cidrs []string, trustWellKnownCloudflare bool) *ClientIPResolver {
	nets := parseCIDRs(cidrs)
	if trustWellKnownCloudflare {
		nets = append(nets, cloudflareNetworks()...)
	}
	return &ClientIPResolver{trustedNets: nets}
}

// Resolve returns the best-known client IP for r.
//
// Algorithm:
//  1. Parse the immediate peer from r.RemoteAddr.
//  2. If the peer is NOT in the trusted set, return the peer. All
//     forwarding headers are ignored. This is the spoof-proof path.
//  3. If the peer IS trusted, walk the forwarding headers in this order:
//     a. CF-Connecting-IP  (set by Cloudflare; if set by anyone else
//        upstream of Cloudflare it is overwritten by Cloudflare on
//        ingress, so it is the most reliable signal we can get).
//     b. X-Forwarded-For   (rightmost non-trusted entry; the leftmost
//        entry is user-supplied and therefore untrusted).
//     c. X-Real-IP         (single value; least preferred because it
//        loses the proxy chain).
//  4. Fall back to the peer if no header yields a parseable IP.
func (r *ClientIPResolver) Resolve(req *http.Request) string {
	peer := peerIP(req.RemoteAddr)

	// Untrusted peer: never honour forwarding headers.
	if !r.isTrusted(peer) {
		if peer != nil {
			return peer.String()
		}
		return req.RemoteAddr
	}

	// Trusted peer: prefer CF-Connecting-IP.
	if v := strings.TrimSpace(req.Header.Get(headerCFConnectingIP)); v != "" {
		if ip := parseIP(v); ip != nil {
			return ip.String()
		}
	}

	// Then walk X-Forwarded-For from right to left; the leftmost
	// entry is the user-supplied claim and is untrusted. The first
	// non-trusted IP from the right is the real client.
	if xff := req.Header.Get(headerXForwardedFor); xff != "" {
		parts := strings.Split(xff, ",")
		for i := len(parts) - 1; i >= 0; i-- {
			ip := parseIP(strings.TrimSpace(parts[i]))
			if ip == nil {
				continue
			}
			if !r.isTrusted(ip) {
				return ip.String()
			}
		}
		// Whole chain is trusted; the leftmost claim is the user.
		if first := parseIP(strings.TrimSpace(parts[0])); first != nil {
			return first.String()
		}
	}

	// X-Real-IP is the last resort.
	if v := strings.TrimSpace(req.Header.Get(headerXRealIP)); v != "" {
		if ip := parseIP(v); ip != nil {
			return ip.String()
		}
	}

	if peer != nil {
		return peer.String()
	}
	return req.RemoteAddr
}

// isTrusted reports whether ip is in any of the configured trusted nets.
// Returns false for a nil ip so an unparseable peer is never treated
// as trusted.
func (r *ClientIPResolver) isTrusted(ip net.IP) bool {
	if ip == nil {
		return false
	}
	for _, n := range r.trustedNets {
		if n.Contains(ip) {
			return true
		}
	}
	return false
}

// peerIP extracts the IP portion of an http.Request RemoteAddr value.
// RemoteAddr is documented as host:port, but a bare host (without a
// port) and IPv6-bracketed values are tolerated for robustness.
func peerIP(remoteAddr string) net.IP {
	if remoteAddr == "" {
		return nil
	}
	host, _, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		host = remoteAddr
	}
	return parseIP(host)
}

// parseIP is a tiny wrapper that strips IPv6 zone identifiers before
// calling net.ParseIP, which does not accept them.
func parseIP(s string) net.IP {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	if idx := strings.IndexByte(s, '%'); idx >= 0 {
		s = s[:idx]
	}
	return net.ParseIP(s)
}

// ParseTrustedCIDRs parses a slice of CIDR strings and returns the
// successfully-parsed networks together with a slice of strings that
// failed to parse. Used by Config validation to surface bad values
// at startup instead of silently ignoring them at request time.
func ParseTrustedCIDRs(cidrs []string) ([]*net.IPNet, []string) {
	var good []*net.IPNet
	var bad []string
	for _, raw := range cidrs {
		raw = strings.TrimSpace(raw)
		if raw == "" {
			continue
		}
		_, n, err := net.ParseCIDR(raw)
		if err != nil {
			bad = append(bad, raw)
			continue
		}
		good = append(good, n)
	}
	return good, bad
}

func parseCIDRs(cidrs []string) []*net.IPNet {
	good, _ := ParseTrustedCIDRs(cidrs)
	return good
}

// ---------------------------------------------------------------------------
// Cloudflare published IP ranges
//
// Source of truth:
//   IPv4: https://www.cloudflare.com/ips-v4
//   IPv6: https://www.cloudflare.com/ips-v6
//
// The lists below are embedded so that the resolver works in
// air-gapped environments and starts up without network access. They
// are also the only ranges Cloudflare uses for proxied traffic, so a
// match here is a strong signal that the immediate peer is a
// Cloudflare edge node.
//
// Operators MUST refresh these lists periodically; Cloudflare
// publishes changes on their status page. A future commit will add
// a refresh script under deployments/cloudflare/.
// ---------------------------------------------------------------------------

var cloudflareIPv4CIDRs = []string{
	"173.245.48.0/20",
	"103.21.244.0/22",
	"103.22.200.0/22",
	"103.31.4.0/22",
	"141.101.64.0/18",
	"108.162.192.0/18",
	"190.93.240.0/20",
	"188.114.96.0/20",
	"197.234.240.0/22",
	"198.41.128.0/17",
	"162.158.0.0/15",
	"104.16.0.0/13",
	"104.24.0.0/14",
	"172.64.0.0/13",
	"131.0.72.0/22",
}

var cloudflareIPv6CIDRs = []string{
	"2400:cb00::/32",
	"2606:4700::/32",
	"2803:f800::/32",
	"2405:b500::/32",
	"2405:8100::/32",
	"2a06:98c0::/29",
	"2c0f:f248::/32",
}

var (
	cloudflareNetsOnce sync.Once
	cloudflareNetsList []*net.IPNet
)

func cloudflareNetworks() []*net.IPNet {
	cloudflareNetsOnce.Do(func() {
		all := append([]string{}, cloudflareIPv4CIDRs...)
		all = append(all, cloudflareIPv6CIDRs...)
		cloudflareNetsList = parseCIDRs(all)
	})
	return cloudflareNetsList
}
