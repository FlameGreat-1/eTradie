package auth

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"path/filepath"
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
// Concurrent use is safe: trustedNets is immutable after construction.
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
//
// This constructor uses ONLY the in-binary embedded Cloudflare list.
// To pick up live-refreshed Cloudflare ranges from a mounted ConfigMap,
// use NewClientIPResolverWithRangesDir. The two-argument form is kept
// for backward compatibility with existing call sites and tests.
func NewClientIPResolver(cidrs []string, trustWellKnownCloudflare bool) *ClientIPResolver {
	return NewClientIPResolverWithRangesDir(cidrs, trustWellKnownCloudflare, "")
}

// NewClientIPResolverWithRangesDir builds a resolver and, when both
// trustWellKnownCloudflare is true AND cloudflareRangesDir is non-empty,
// reads the live-refreshable Cloudflare IPv4 / IPv6 published ranges
// from <cloudflareRangesDir>/ipv4.txt and <cloudflareRangesDir>/ipv6.txt.
//
// Behaviour matrix:
//
//	trustCF=false:                            embedded list ignored, dir ignored.
//	trustCF=true,  dir="":                    embedded list used.
//	trustCF=true,  dir="/etc/.../cloudflare": file ranges used; on read error,
//	                                          falls back to embedded list.
//
// File ranges REPLACE the embedded list when both could apply, so a
// freshly-published Cloudflare range that is only in the file is
// honoured immediately and a stale entry only in the embedded list
// does not silently leak through. This matches the chart's documented
// contract that the mounted ConfigMap is the source of truth at runtime.
func NewClientIPResolverWithRangesDir(cidrs []string, trustWellKnownCloudflare bool, cloudflareRangesDir string) *ClientIPResolver {
	nets := parseCIDRs(cidrs)
	if trustWellKnownCloudflare {
		cfNets := loadCloudflareNetsForResolver(cloudflareRangesDir)
		nets = append(nets, cfNets...)
	}
	return &ClientIPResolver{trustedNets: nets}
}

// loadCloudflareNetsForResolver returns the *net.IPNet list to trust
// for Cloudflare. When dir is set and readable, file contents are used.
// On any error (missing dir, unreadable, all entries malformed) it
// falls back to the in-binary embedded list AND increments the
// auth_cloudflare_ranges_fallback_total counter so monitoring can
// detect silent degradation. The fallback is what makes this change
// safe to roll out before every cluster has the ConfigMap mounted:
// existing deployments keep working with the embedded list.
func loadCloudflareNetsForResolver(dir string) []*net.IPNet {
	if dir == "" {
		// Empty dir is the explicit "do not use file path" signal,
		// not a fallback. No metric increment.
		return cloudflareNetworks()
	}
	nets, bad, err := LoadCloudflareNetworksFromDir(dir)
	if err != nil {
		fmt.Fprintf(os.Stderr,
			"auth/clientip: cloudflare ranges dir %q unreadable (%v); falling back to embedded list\n",
			dir, err)
		CloudflareRangesFallbackTotal.WithLabelValues("unreadable").Inc()
		return cloudflareNetworks()
	}
	if len(nets) == 0 {
		reason := "empty"
		if len(bad) > 0 {
			reason = "malformed_only"
		}
		fmt.Fprintf(os.Stderr,
			"auth/clientip: cloudflare ranges dir %q produced 0 valid networks (bad=%d); falling back to embedded list\n",
			dir, len(bad))
		CloudflareRangesFallbackTotal.WithLabelValues(reason).Inc()
		return cloudflareNetworks()
	}
	if len(bad) > 0 {
		// Partial-malformed is NOT a fallback: we still use the file
		// data. Surface the warning so operators can fix bad lines
		// but do not page on it (no metric increment).
		fmt.Fprintf(os.Stderr,
			"auth/clientip: cloudflare ranges dir %q had %d malformed entries (using %d valid)\n",
			dir, len(bad), len(nets))
	}
	return nets
}

// LoadCloudflareNetworksFromDir reads ipv4.txt and ipv6.txt from dir
// and returns parsed networks plus any malformed lines for surface-up
// validation by callers (config validators, tests). Comment lines
// starting with '#' and blank lines are skipped, matching the format
// produced by deployments/cloudflare/scripts/refresh-cloudflare-ips.sh
// and the chart at helm/gateway/files/cloudflare/.
//
// If neither file exists, returns (nil, nil, os.ErrNotExist) so the
// caller can distinguish "deliberately not configured" from a real
// I/O error.
func LoadCloudflareNetworksFromDir(dir string) ([]*net.IPNet, []string, error) {
	if dir == "" {
		return nil, nil, fmt.Errorf("empty cloudflare ranges dir")
	}
	ipv4Path := filepath.Join(dir, "ipv4.txt")
	ipv6Path := filepath.Join(dir, "ipv6.txt")

	ipv4Lines, err4 := readCIDRFile(ipv4Path)
	ipv6Lines, err6 := readCIDRFile(ipv6Path)

	// If both files are missing, surface ErrNotExist so callers can
	// fall back without treating it as a hard error.
	if err4 != nil && os.IsNotExist(err4) && err6 != nil && os.IsNotExist(err6) {
		return nil, nil, os.ErrNotExist
	}
	// Any other error on either file is propagated.
	if err4 != nil && !os.IsNotExist(err4) {
		return nil, nil, fmt.Errorf("read %s: %w", ipv4Path, err4)
	}
	if err6 != nil && !os.IsNotExist(err6) {
		return nil, nil, fmt.Errorf("read %s: %w", ipv6Path, err6)
	}

	all := append([]string{}, ipv4Lines...)
	all = append(all, ipv6Lines...)
	nets, bad := ParseTrustedCIDRs(all)
	return nets, bad, nil
}

// readCIDRFile reads a CIDR-per-line text file. Returns the non-empty,
// non-comment lines verbatim (validation happens in the caller).
func readCIDRFile(path string) ([]string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, raw := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(raw)
		if line == "" {
			continue
		}
		if strings.HasPrefix(line, "#") {
			continue
		}
		out = append(out, line)
	}
	return out, nil
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
// Cloudflare published IP ranges (embedded fallback)
//
// Source of truth at build time:
//   IPv4: https://www.cloudflare.com/ips-v4
//   IPv6: https://www.cloudflare.com/ips-v6
//
// The lists below are embedded so that the resolver works in
// air-gapped environments and starts up without network access. They
// are also the only ranges Cloudflare uses for proxied traffic, so a
// match here is a strong signal that the immediate peer is a
// Cloudflare edge node.
//
// At runtime, the file-loader path above (LoadCloudflareNetworksFromDir)
// is preferred when AUTH_CLOUDFLARE_RANGES_DIR points at a directory
// containing fresh ipv4.txt / ipv6.txt files. The embedded list is the
// fallback for clusters that have not yet mounted the chart-published
// ConfigMap.
//
// deployments/cloudflare/scripts/refresh-cloudflare-ips.sh updates the
// chart-published files weekly via CI; this embedded list only needs
// to be refreshed when the binary is rebuilt.
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
