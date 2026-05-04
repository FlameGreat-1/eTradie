package auth

import (
	"net/http"
	"os"
	"path/filepath"
	"testing"
)

func newReq(remoteAddr string, headers map[string]string) *http.Request {
	r := &http.Request{
		RemoteAddr: remoteAddr,
		Header:     http.Header{},
	}
	for k, v := range headers {
		r.Header.Set(k, v)
	}
	return r
}

func TestResolver_UntrustedPeerIgnoresForwardingHeaders(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8"}, false)
	req := newReq("203.0.113.7:54321", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
		"X-Forwarded-For":  "198.51.100.2, 10.0.0.1",
		"X-Real-IP":        "198.51.100.3",
	})
	got := r.Resolve(req)
	if got != "203.0.113.7" {
		t.Fatalf("untrusted peer should win, got %q", got)
	}
}

func TestResolver_TrustedPeerPrefersCFConnectingIP(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8"}, false)
	req := newReq("10.0.0.5:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
		"X-Forwarded-For":  "198.51.100.99, 10.0.0.5",
		"X-Real-IP":        "198.51.100.42",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("CF-Connecting-IP should win for trusted peer, got %q", got)
	}
}

func TestResolver_XFFRightToLeftSkipsTrustedHops(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8", "172.16.0.0/12"}, false)
	req := newReq("10.0.0.5:443", map[string]string{
		"X-Forwarded-For": "203.0.113.7, 172.16.5.1, 10.0.0.5",
	})
	got := r.Resolve(req)
	if got != "203.0.113.7" {
		t.Fatalf("first non-trusted entry from the right should win, got %q", got)
	}
}

func TestResolver_XRealIPFallback(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8"}, false)
	req := newReq("10.0.0.5:443", map[string]string{
		"X-Real-IP": "198.51.100.7",
	})
	got := r.Resolve(req)
	if got != "198.51.100.7" {
		t.Fatalf("X-Real-IP should be used when no other header present, got %q", got)
	}
}

func TestResolver_CloudflareWellKnownRangesHonoured(t *testing.T) {
	r := NewClientIPResolver(nil, true)
	// 162.158.0.0/15 is a Cloudflare published IPv4 range.
	req := newReq("162.158.1.1:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("Cloudflare-edge peer should be trusted, got %q", got)
	}
}

func TestResolver_CloudflareDisabledByDefault(t *testing.T) {
	r := NewClientIPResolver(nil, false)
	req := newReq("162.158.1.1:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "162.158.1.1" {
		t.Fatalf("without CF trust, peer should win, got %q", got)
	}
}

func TestResolver_SpoofedCFHeaderFromUntrustedPeerRejected(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8"}, true)
	// Attacker bypasses Cloudflare, hits origin directly from
	// 198.51.100.7, and injects a fake CF-Connecting-IP. The
	// resolver must NOT honour the header because the peer is
	// outside the trusted set (not a real CF edge IP).
	req := newReq("198.51.100.7:31337", map[string]string{
		"CF-Connecting-IP": "127.0.0.1",
		"X-Forwarded-For":  "127.0.0.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.7" {
		t.Fatalf("spoofed header from untrusted peer must be rejected, got %q", got)
	}
}

func TestResolver_IPv6ZoneStripped(t *testing.T) {
	r := NewClientIPResolver([]string{"::/0"}, false)
	req := newReq("[fe80::1%eth0]:443", map[string]string{})
	got := r.Resolve(req)
	if got != "fe80::1" {
		t.Fatalf("IPv6 zone identifier should be stripped, got %q", got)
	}
}

func TestResolver_BareHostNoPort(t *testing.T) {
	r := NewClientIPResolver([]string{"10.0.0.0/8"}, false)
	req := newReq("10.0.0.5", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("bare-host RemoteAddr should still resolve trusted peer, got %q", got)
	}
}

func TestParseTrustedCIDRs_SurfacesBadValues(t *testing.T) {
	good, bad := ParseTrustedCIDRs([]string{
		"10.0.0.0/8",
		"not-a-cidr",
		"   ",
		"172.16.0.0/12",
		"999.999.999.999/8",
	})
	if len(good) != 2 {
		t.Fatalf("want 2 good CIDRs, got %d", len(good))
	}
	if len(bad) != 2 {
		t.Fatalf("want 2 bad CIDRs surfaced, got %d (%v)", len(bad), bad)
	}
}

// ---------------------------------------------------------------------------
// File-loader path tests (NewClientIPResolverWithRangesDir +
// LoadCloudflareNetworksFromDir).
// ---------------------------------------------------------------------------

func writeRangesFiles(t *testing.T, dir, ipv4, ipv6 string) {
	t.Helper()
	if ipv4 != "" {
		if err := os.WriteFile(filepath.Join(dir, "ipv4.txt"), []byte(ipv4), 0o644); err != nil {
			t.Fatalf("write ipv4.txt: %v", err)
		}
	}
	if ipv6 != "" {
		if err := os.WriteFile(filepath.Join(dir, "ipv6.txt"), []byte(ipv6), 0o644); err != nil {
			t.Fatalf("write ipv6.txt: %v", err)
		}
	}
}

func TestLoadCloudflareNetworksFromDir_HappyPath(t *testing.T) {
	dir := t.TempDir()
	writeRangesFiles(t, dir,
		"# header\n203.0.113.0/24\n198.51.100.0/24\n",
		"# v6\n2001:db8::/32\n")

	nets, bad, err := LoadCloudflareNetworksFromDir(dir)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(bad) != 0 {
		t.Fatalf("unexpected bad lines: %v", bad)
	}
	if len(nets) != 3 {
		t.Fatalf("want 3 nets, got %d", len(nets))
	}
}

func TestLoadCloudflareNetworksFromDir_MissingDirIsSoftSignal(t *testing.T) {
	_, _, err := LoadCloudflareNetworksFromDir(filepath.Join(t.TempDir(), "does-not-exist"))
	if !os.IsNotExist(err) {
		t.Fatalf("want os.ErrNotExist, got %v", err)
	}
}

func TestLoadCloudflareNetworksFromDir_MalformedLinesSurfaced(t *testing.T) {
	dir := t.TempDir()
	writeRangesFiles(t, dir,
		"203.0.113.0/24\nnot-a-cidr\n",
		"# none\n")

	nets, bad, err := LoadCloudflareNetworksFromDir(dir)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(nets) != 1 {
		t.Fatalf("want 1 valid net, got %d", len(nets))
	}
	if len(bad) != 1 || bad[0] != "not-a-cidr" {
		t.Fatalf("want 1 bad line surfaced, got %v", bad)
	}
}

func TestNewClientIPResolverWithRangesDir_FileRangesReplaceEmbedded(t *testing.T) {
	// File contains a range that is NOT in the embedded list. With the
	// file-loader path, that range must be honoured.
	dir := t.TempDir()
	writeRangesFiles(t, dir,
		"203.0.113.0/24\n",
		"")

	r := NewClientIPResolverWithRangesDir(nil, true, dir)
	req := newReq("203.0.113.55:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("file-derived range should be trusted, got %q", got)
	}
}

func TestNewClientIPResolverWithRangesDir_MissingDirFallsBackToEmbedded(t *testing.T) {
	// dir is set but does not exist: must fall back to the embedded
	// list. 162.158.0.0/15 is in the embedded list.
	r := NewClientIPResolverWithRangesDir(nil, true, filepath.Join(t.TempDir(), "absent"))
	req := newReq("162.158.1.1:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("missing dir should fall back to embedded list, got %q", got)
	}
}

func TestNewClientIPResolverWithRangesDir_EmptyDirKeepsEmbedded(t *testing.T) {
	// dir == "" is the back-compat path: should match the
	// 2-arg constructor exactly. 162.158.0.0/15 is embedded.
	r := NewClientIPResolverWithRangesDir(nil, true, "")
	req := newReq("162.158.1.1:443", map[string]string{
		"CF-Connecting-IP": "198.51.100.1",
	})
	got := r.Resolve(req)
	if got != "198.51.100.1" {
		t.Fatalf("empty dir should keep embedded behaviour, got %q", got)
	}
}

func TestLoadCloudflareNetworksFromDir_CommentsAndBlankLines(t *testing.T) {
	dir := t.TempDir()
	writeRangesFiles(t, dir,
		"# top\n\n   \n203.0.113.0/24\n# tail\n",
		"")

	nets, bad, err := LoadCloudflareNetworksFromDir(dir)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(bad) != 0 {
		t.Fatalf("unexpected bad lines: %v", bad)
	}
	if len(nets) != 1 {
		t.Fatalf("want 1 net, got %d", len(nets))
	}
}
